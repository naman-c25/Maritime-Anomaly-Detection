"""End-to-end vision branch: frames → ROI/CLAHE → YOLOv8 + tracker → zone/dwell rules → events and s_vision."""
import json
import shutil
import subprocess
from pathlib import Path

import cv2
import numpy as np

from .config import resolve_detector, resolve_path
from .geo import CameraProjection
from .preprocess import apply_roi, maybe_clahe
from .rules import TrackRules, point_in_polygon
from .scoring import summarise_tracks
from .tracking import VesselTracker, class_ids

COLORS = {"normal": (60, 200, 60), "zone": (40, 40, 230), "loiter": (200, 60, 200)}
MAX_OUT_WIDTH = 1280


def _draw(frame, box, label, color, scale=1.0):
    x1, y1, x2, y2 = (int(v * scale) for v in box.xyxy)
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
    y0 = max(th + 6, y1)
    cv2.rectangle(frame, (x1, y0 - th - 6), (x1 + tw + 6, y0), color, -1)
    cv2.putText(frame, label, (x1 + 3, y0 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)


def _draw_zones(frame, cam, scale=1.0):
    for z in cam.get("restricted_zones", []):
        pts = (np.asarray(z["polygon"], np.float32) * scale).astype(np.int32)
        overlay = frame.copy()
        cv2.fillPoly(overlay, [pts], COLORS["zone"])
        cv2.addWeighted(overlay, 0.12, frame, 0.88, 0, frame)
        cv2.polylines(frame, [pts], True, COLORS["zone"], 2)
        x, y = pts[:, 0].min(), pts[:, 1].max()
        cv2.putText(frame, z["name"], (int(x) + 8, int(y) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLORS["zone"], 2,
                    cv2.LINE_AA)


def to_browser_mp4(src, dst):
    """Re-encodes to H.264 + faststart so browsers can play it. Falls back to a copy without ffmpeg."""
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        exe = shutil.which("ffmpeg")
    if not exe:
        shutil.copy(src, dst)
        return False
    cmd = [exe, "-y", "-loglevel", "error", "-i", str(src), "-c:v", "libx264", "-preset", "veryfast", "-crf", "26",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(dst)]
    subprocess.run(cmd, check=True)
    return True


def scale_camera(cam, width, height):
    """Rescales a camera's pixel coordinates (ROI, zones, GCPs) when the video size differs from `frame_size`."""
    size = cam.get("frame_size")
    if not size or (size[0] == width and size[1] == height) or not width or not height:
        return cam
    sx, sy = width / size[0], height / size[1]
    sc = lambda pts: [[x * sx, y * sy] for x, y in pts]   # noqa: E731
    out = dict(cam, frame_size=[width, height])
    if cam.get("roi"):
        out["roi"] = sc(cam["roi"])
    out["restricted_zones"] = [dict(z, polygon=sc(z["polygon"])) for z in cam.get("restricted_zones", [])]
    if cam.get("gcp"):
        out["gcp"] = dict(cam["gcp"], pixel=sc(cam["gcp"]["pixel"]))
    return out


def frame_stride(cfg, fps):
    inf = cfg["inference"]
    if inf.get("frame_stride"):
        return max(1, int(inf["frame_stride"]))
    target = inf.get("target_fps") or fps
    return max(1, int(round(fps / target)))


def process_video(video_path, cfg, cam, weights=None, out_dir="outputs", tracker=None, use_clahe=None,
                  use_dwell=True, write_video=True, start_time=0.0, progress=None, max_seconds=None):
    """Runs the vision branch on one video. `start_time` (Unix seconds) aligns frame times with AIS timestamps.

    `progress(done_frames, total_frames)` is called while processing; `max_seconds` stops after that much video.
    """
    inf, rules_cfg = cfg["inference"], cfg["rules"]
    tracker = tracker or cfg["tracking"]["tracker"]
    class_names = None
    if weights is None:
        weights, class_names, _ = resolve_detector(cfg)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise IOError(f"cannot open video {video_path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    if max_seconds:
        total = min(total, int(max_seconds * fps)) if total else int(max_seconds * fps)
    stride = frame_stride(cfg, fps)
    cam = scale_camera(cam, w, h)

    vt = VesselTracker(weights, tracker, inf["conf"], inf["iou"], cfg["model"]["imgsz"], inf["device"],
                       cfg["tracking"].get("deepsort_max_age", 30), class_names=class_names,
                       bytetrack_cfg=resolve_path(cfg["tracking"].get("bytetrack_cfg", "bytetrack.yaml"))
                       if cfg["tracking"].get("bytetrack_cfg") else "bytetrack.yaml")
    dwell = cam.get("dwell_seconds", rules_cfg["dwell_seconds"])
    radius = cam.get("loiter_radius_px", rules_cfg["loiter_radius_px"])
    rules = TrackRules(cam.get("restricted_zones", []), dwell, radius, use_dwell)
    proj = CameraProjection.from_camera(cam)

    scale = min(1.0, MAX_OUT_WIDTH / w) if w else 1.0
    out_size = (int(w * scale) // 2 * 2, int(h * scale) // 2 * 2)
    raw_path = out_dir / "annotated_raw.mp4"
    writer = None
    if write_video:
        writer = cv2.VideoWriter(str(raw_path), cv2.VideoWriter_fourcc(*"mp4v"), fps / stride, out_size)

    events, mot_lines, idx, clahe_frames, processed = [], [], 0, 0, 0
    paths = {}
    while True:
        if total and idx >= total:
            break
        ok, frame = cap.read()
        if not ok:
            break
        if idx % stride:
            idx += 1
            continue
        t = start_time + idx / fps
        work = apply_roi(frame, cam.get("roi"))
        work, applied = maybe_clahe(work, inf["clahe"], force=use_clahe)   # None = auto (low-light only)
        clahe_frames += applied
        out = cv2.resize(frame, out_size) if writer is not None and scale != 1.0 else frame

        for box in vt.update(work):
            x1, y1, x2, y2 = box.xyxy
            ground = ((x1 + x2) / 2.0, y2)                     # waterline point of the hull
            new = rules.update(box.track_id, ground, t, box.conf)
            for e in new:
                e["frame"] = idx
                if proj:
                    e["lat"], e["lon"] = (round(v, 6) for v in proj.pixel_to_latlon(ground))
            events += new
            if proj and processed % 3 == 0:
                lat, lon = proj.pixel_to_latlon(ground)
                paths.setdefault(box.track_id, []).append([round(lat, 6), round(lon, 6)])
            mot_lines.append(f"{idx + 1},{box.track_id},{x1:.1f},{y1:.1f},{x2 - x1:.1f},{y2 - y1:.1f},{box.conf:.3f},-1,-1,-1")
            if writer is not None:
                st = rules.tracks[box.track_id]
                kind = "zone" if st.zones_inside else ("loiter" if st.loitering else "normal")
                tag = " ZONE" if kind == "zone" else (" LOITER" if kind == "loiter" else "")
                _draw(out, box, f"ID {box.track_id} {box.conf:.2f}{tag}", COLORS[kind], scale)
        if writer is not None:
            _draw_zones(out, cam, scale)
            writer.write(out)
        processed += 1
        idx += 1
        if progress and processed % 5 == 0:
            progress(idx, total)

    cap.release()
    video_file = None
    if writer is not None:
        writer.release()
        final = out_dir / "annotated.mp4"
        to_browser_mp4(raw_path, final)
        raw_path.unlink(missing_ok=True)
        video_file = final.name
    (out_dir / "tracks_mot.txt").write_text("\n".join(mot_lines) + "\n", encoding="utf-8")
    tracks = summarise_tracks(rules, proj.pixel_to_latlon if proj else None)
    for tr in tracks:
        tr["path"] = paths.get(tr["track_id"], [])
    summary = {"video": str(video_path), "fps": fps, "frames": idx, "processed_frames": processed,
               "frame_stride": stride, "duration_s": round(idx / fps, 2), "tracker": tracker,
               "weights": Path(str(weights)).name, "clahe_frames": int(clahe_frames), "start_time": start_time,
               "events": events, "tracks": tracks, "annotated_video": video_file}
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if progress:
        progress(idx, total or idx)
    return summary


def process_image(image_bgr, cfg, cam, model, class_names=None):
    """Single-image detection with zone flags (no tracking or dwell time)."""
    inf = cfg["inference"]
    if cam:
        cam = scale_camera(cam, image_bgr.shape[1], image_bgr.shape[0])
    work, applied = maybe_clahe(apply_roi(image_bgr, cam.get("roi") if cam else None), inf["clahe"])
    r = model.predict(work, conf=inf["conf"], iou=inf["iou"], imgsz=cfg["model"]["imgsz"], device=inf["device"],
                      classes=class_ids(model, class_names), verbose=False)[0]
    zones = cam.get("restricted_zones", []) if cam else []
    dets = []
    annotated = image_bgr.copy()
    for (x1, y1, x2, y2), c in zip(r.boxes.xyxy.tolist(), r.boxes.conf.tolist()):
        ground = ((x1 + x2) / 2.0, y2)
        inside = [z["name"] for z in zones if point_in_polygon(ground, z["polygon"])]
        dets.append({"box": [round(v, 1) for v in (x1, y1, x2, y2)], "conf": round(c, 4), "zones": inside,
                     "s_vision": round(c, 4) if inside else 0.0})
        color = COLORS["zone"] if inside else COLORS["normal"]
        cv2.rectangle(annotated, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
        cv2.putText(annotated, f"{c:.2f}", (int(x1), max(15, int(y1) - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    _draw_zones(annotated, cam or {})
    return {"clahe": applied, "detections": dets, "annotated": annotated}
