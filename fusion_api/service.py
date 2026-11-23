"""State of the integrated system: latest AIS analysis, latest vision run, fused alerts and background jobs.

Everything is kept in memory (one demo/operator session per server). On start-up the demo scenario is loaded:
the AIS demo file is scored immediately and the vision result comes from demo/cache, which is rebuilt in the
background whenever the detector weights change (so pushing a new best.pt is enough to refresh the demo).
"""
import copy
import glob
import hashlib
import json
import shutil
import threading
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from ais_detection.ais_model import FEATURE_LABELS, AisModel, QuantileScorer, analyze_dataframe, exp_tail_score
from computer_vision.config import ROOT, load_cameras, load_config, resolve_detector, resolve_path
from fusion_api.fusion import AisScorer, build_alerts

MEDIA = ROOT / "outputs" / "media"
DEMO_CACHE = ROOT / "computer_vision" / "demo" / "cache"


def _file_sig(path):
    p = Path(path)
    if not p.exists():
        return f"auto:{p.name}"
    h = hashlib.sha1()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _iso(t):
    return pd.Timestamp(t, unit="s", tz="UTC").strftime("%Y-%m-%dT%H:%M:%SZ") if t is not None else None


class Service:
    def __init__(self, config_path=None):
        self.cfg = load_config(config_path)
        self.cameras = load_cameras(self.cfg["rules"]["cameras_file"])
        self.ais_model = AisModel(resolve_path(self.cfg["ais"]["model_dir"]))
        if self.cfg["fusion"].get("ais_threshold") is None:
            self.cfg["fusion"]["ais_threshold"] = self.ais_model.threshold
        val = resolve_path(self.cfg["ais"].get("validation_errors") or "missing.npy")
        quant = resolve_path(self.cfg["ais"].get("error_quantiles") or "missing.json")
        if val.exists():
            self.scorer, self.scorer_kind = AisScorer(np.load(val)), "percentile of validation errors"
        elif quant.exists():
            self.scorer = QuantileScorer(json.loads(quant.read_text(encoding="utf-8"))["quantiles"])
            self.scorer_kind = "percentile of training errors (notebook quantiles)"
        else:
            tau = self.cfg["fusion"]["ais_threshold"]
            self.scorer, self.scorer_kind = (lambda e: exp_tail_score(e, tau)), "exponential tail at τ"
        self.lock = threading.RLock()
        self.pool = ThreadPoolExecutor(max_workers=1)   # one CPU-heavy vision job at a time
        self.jobs = {}
        self.ais = None          # full analysis (with per-window points)
        self.ais_source = None
        self.vision = None       # summary of the latest vision run
        self.vision_source = None
        self.alerts = []
        self.alert_status = {}
        self.updated_at = time.time()
        MEDIA.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ detector
    def detector_info(self):
        weights, classes, fallback = resolve_detector(self.cfg)
        return {"weights": Path(weights).name, "fallback": fallback, "classes": classes,
                "note": ("COCO-pretrained YOLOv8 (boat class) — replace with the fine-tuned vessel model"
                         if fallback else "fine-tuned vessel detector")}

    # ------------------------------------------------------------------ AIS
    def load_ais_csv(self, path_or_buffer, source):
        df = pd.read_csv(path_or_buffer)
        result = analyze_dataframe(df, self.ais_model)
        with self.lock:
            self.ais, self.ais_source = result, source
            self._recompute()
        return result

    # ------------------------------------------------------------------ vision
    def default_start_time(self):
        demo_t = pd.Timestamp(self.cfg["demo"]["start_time"]).timestamp()
        tr = self.ais and self.ais.get("time_range")
        if tr and not (tr[0] <= demo_t <= tr[1]):
            return tr[1] - 60.0
        return demo_t

    def set_vision(self, summary, source, media_url=None):
        with self.lock:
            summary = dict(summary, media_url=media_url)
            self.vision, self.vision_source = summary, source
            self._recompute()

    def submit_video(self, video_path, camera, start_time, source, keep_input=False):
        job_id = uuid.uuid4().hex[:10]
        self.jobs[job_id] = {"id": job_id, "kind": "video", "status": "queued", "progress": 0.0, "source": source,
                             "created": time.time(), "error": None}
        self.pool.submit(self._run_video, job_id, Path(video_path), camera, start_time, source, keep_input)
        return self.jobs[job_id]

    def _run_video(self, job_id, video_path, camera, start_time, source, keep_input):
        from computer_vision.pipeline import process_video
        job = self.jobs[job_id]
        job["status"] = "running"
        out_dir = MEDIA / job_id
        t0 = time.time()
        try:
            def prog(done, total):
                job["progress"] = round(min(1.0, done / total), 3) if total else 0.0
            summary = process_video(video_path, self.cfg, self.cameras[camera], out_dir=out_dir,
                                    start_time=start_time, progress=prog,
                                    max_seconds=self.cfg["inference"].get("max_video_seconds"))
            elapsed = time.time() - t0
            summary.update(camera=camera, processing_s=round(elapsed, 1),
                           processing_fps=round(summary["processed_frames"] / elapsed, 2) if elapsed else None)
            url = f"/api/media/{job_id}/{summary['annotated_video']}" if summary.get("annotated_video") else None
            self.set_vision(summary, source, url)
            job.update(status="done", progress=1.0, finished=time.time())
        except Exception as e:   # reported to the UI
            traceback.print_exc()
            job.update(status="error", error=str(e))
        finally:
            if not keep_input:
                video_path.unlink(missing_ok=True)

    def analyse_image(self, image_bgr, camera):
        import cv2
        from ultralytics import YOLO
        from computer_vision.pipeline import process_image
        weights, classes, _ = resolve_detector(self.cfg)
        res = process_image(image_bgr, self.cfg, self.cameras.get(camera), YOLO(weights), classes)
        name = uuid.uuid4().hex[:10]
        (MEDIA / name).mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(MEDIA / name / "annotated.jpg"), res.pop("annotated"))
        res["media_url"] = f"/api/media/{name}/annotated.jpg"
        return res

    # ------------------------------------------------------------------ demo
    def demo_signature(self):
        weights, classes, _ = resolve_detector(self.cfg)
        cam = self.cameras[self.cfg["demo"]["camera"]]
        keys = {"weights": _file_sig(weights),
                "classes": classes, "camera": cam, "inference": self.cfg["inference"], "rules": self.cfg["rules"],
                "tracking": self.cfg["tracking"], "video": _file_sig(resolve_path(self.cfg["demo"]["video"])),
                "start_time": self.cfg["demo"]["start_time"]}
        return hashlib.sha1(json.dumps(keys, sort_keys=True, default=str).encode()).hexdigest()

    def load_demo(self, rebuild_if_stale=True):
        """Loads the demo AIS scenario and the cached demo vision run (rebuilding the cache in the background)."""
        d = self.cfg["demo"]
        self.load_ais_csv(resolve_path(d["ais_csv"]), "demo: simulated AIS scenario (Singapore Strait)")
        meta = DEMO_CACHE / "meta.json"
        sig = self.demo_signature()
        if meta.exists() and json.loads(meta.read_text())["signature"] == sig:
            summary = json.loads((DEMO_CACHE / "summary.json").read_text(encoding="utf-8"))
            self.set_vision(summary, "demo: Singapore Maritime Dataset clip MVI_1486_VIS",
                            "/api/media/demo/annotated.mp4")
            return None
        with self.lock:
            self.vision, self.vision_source = None, None
            self._recompute()
        if rebuild_if_stale:
            return self.rebuild_demo_cache(sig)
        return None

    def rebuild_demo_cache(self, sig=None):
        sig = sig or self.demo_signature()
        job_id = "demo-" + uuid.uuid4().hex[:6]
        self.jobs[job_id] = {"id": job_id, "kind": "demo", "status": "queued", "progress": 0.0,
                             "source": "demo", "created": time.time(), "error": None}

        def run():
            from computer_vision.pipeline import process_video
            job = self.jobs[job_id]
            job["status"] = "running"
            t0 = time.time()
            try:
                tmp = DEMO_CACHE.with_name("cache_tmp")
                shutil.rmtree(tmp, ignore_errors=True)
                d = self.cfg["demo"]

                def prog(done, total):
                    job["progress"] = round(min(1.0, done / total), 3) if total else 0.0
                summary = process_video(resolve_path(d["video"]), self.cfg, self.cameras[d["camera"]], out_dir=tmp,
                                        start_time=pd.Timestamp(d["start_time"]).timestamp(), progress=prog)
                elapsed = time.time() - t0
                summary.update(camera=d["camera"], video="demo_clip.mp4", processing_s=round(elapsed, 1),
                               processing_fps=round(summary["processed_frames"] / elapsed, 2))
                (tmp / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
                (tmp / "meta.json").write_text(json.dumps({"signature": sig, "built": time.time()}), encoding="utf-8")
                shutil.rmtree(DEMO_CACHE, ignore_errors=True)
                tmp.rename(DEMO_CACHE)
                if self.vision_source is None or self.vision_source.startswith("demo"):
                    self.set_vision(summary, "demo: Singapore Maritime Dataset clip MVI_1486_VIS",
                                    "/api/media/demo/annotated.mp4")
                job.update(status="done", progress=1.0, finished=time.time())
            except Exception as e:
                traceback.print_exc()
                job.update(status="error", error=str(e))

        self.pool.submit(run)
        return self.jobs[job_id]

    # ------------------------------------------------------------------ fusion
    def _ais_points(self):
        if not self.ais:
            return []
        return [p for v in self.ais["vessels"] for p in v.get("points", [])]

    def _recompute(self):
        tracks = self.vision["tracks"] if self.vision else []
        alerts = build_alerts(tracks, self._ais_points(), self.scorer, self.cfg, FEATURE_LABELS)
        names = {v["mmsi"]: v["name"] for v in (self.ais or {}).get("vessels", [])}
        for a in alerts:
            a["id"] = f"CAM-{a['track_id']}" if a["source"] == "camera" else f"AIS-{a['mmsi']}"
            a["status"] = self.alert_status.get(a["id"], "Active")
            a["name"] = a.get("name") or names.get(a["mmsi"]) or (
                f"Camera track {a['track_id']}" if a["source"] == "camera" else f"MMSI {a['mmsi']}")
            a["time"] = _iso(a.get("t"))
        self.alerts = alerts
        self.updated_at = time.time()

    def update_settings(self, alpha=None, levels=None, d_max_m=None, dt_s=None):
        with self.lock:
            f = self.cfg["fusion"]
            if alpha is not None:
                f["alpha"] = float(alpha)
            if levels:
                f["levels"].update({k: float(v) for k, v in levels.items() if k in f["levels"]})
            if d_max_m is not None:
                f["d_max_m"] = float(d_max_m)
            if dt_s is not None:
                f["dt_s"] = float(dt_s)
            self._recompute()

    def set_alert_status(self, alert_id, status):
        with self.lock:
            self.alert_status[alert_id] = status
            for a in self.alerts:
                if a["id"] == alert_id:
                    a["status"] = status

    # ------------------------------------------------------------------ snapshot for the UI
    def settings(self):
        f = self.cfg["fusion"]
        return {"alpha": f["alpha"], "levels": f["levels"], "d_max_m": f["d_max_m"], "dt_s": f["dt_s"],
                "ais_threshold": f["ais_threshold"], "s_ais_mapping": self.scorer_kind,
                "dwell_seconds": self.cfg["rules"]["dwell_seconds"], "conf": self.cfg["inference"]["conf"],
                "tracker": self.cfg["tracking"]["tracker"], "target_fps": self.cfg["inference"].get("target_fps")}

    def camera_geometry(self):
        """Camera position and restricted zones projected to lat/lon (for the map)."""
        from computer_vision.geo import CameraProjection
        out = {}
        for k, cam in self.cameras.items():
            proj = CameraProjection.from_camera(cam)
            zones = []
            if proj:
                for z in cam.get("restricted_zones", []):
                    zones.append({"name": z["name"], "polygon": [[round(a, 6), round(b, 6)] for a, b in
                                                                 (proj.pixel_to_latlon(pt) for pt in z["polygon"])]})
            out[k] = {"name": cam.get("name", k), "description": cam.get("description"),
                      "position": cam.get("position"), "frame_size": cam.get("frame_size"), "zones": zones}
        return out

    def evaluation(self):
        """Detector test results written by scripts/evaluate_detector.py (results/detector_*.json), if present."""
        out = {}
        for p in sorted(glob.glob(str(ROOT / "computer_vision" / "results" / "detector_*.json"))):
            try:
                out[Path(p).stem.replace("detector_", "")] = json.loads(Path(p).read_text(encoding="utf-8"))
            except Exception:
                pass
        return out

    def snapshot(self):
        with self.lock:
            ais = None
            if self.ais:
                ais = {k: v for k, v in self.ais.items() if k != "vessels"}
                ais["vessels"] = [{k: v for k, v in ves.items() if k != "points"} for ves in self.ais["vessels"]]
                errs = [p["recon_error"] for p in self._ais_points()]
                if not errs:
                    errs = [s[1] for ves in self.ais["vessels"] for s in ves.get("series", [])]
                if errs:
                    logs = np.log10(np.clip(errs, 1e-4, None))
                    hist, bins = np.histogram(logs, bins=24)
                    ais["error_histogram"] = [{"log10_error": round(float((bins[i] + bins[i + 1]) / 2), 3),
                                               "count": int(c)} for i, c in enumerate(hist)]
                ais["source"] = self.ais_source
            vision = copy.deepcopy(self.vision) if self.vision else None
            if vision:
                vision["source"] = self.vision_source
                vision.pop("video", None)
            running = [j for j in self.jobs.values() if j["status"] in ("queued", "running")]
            return {"updated_at": self.updated_at, "ais": ais, "vision": vision, "alerts": self.alerts,
                    "settings": self.settings(), "detector": self.detector_info(), "ais_model": self.ais_model.info,
                    "cameras": self.camera_geometry(),
                    "jobs": running, "evaluation": self.evaluation()}
