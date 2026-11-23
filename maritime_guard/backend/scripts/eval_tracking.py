"""Table 9 and the zone/loitering event results: ByteTrack vs DeepSORT on annotated test clips.

Each clip needs, next to the video, `<name>_gt.txt` (MOT format, e.g. CVAT "MOT 1.1" export) and optionally
`<name>_events.csv` (type,start_s,end_s). The camera key is given per clip in a small JSON list:
    [{"video": "clips/cam1_a.mp4", "camera": "harbour_cam_1"}, ...]

    python scripts/eval_tracking.py --clips clips.json --weights models/vessel_yolov8s_best.pt
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from mcv.config import ROOT, load_cameras, load_config  # noqa: E402
from mcv.metrics import event_metrics, load_gt_events, tracking_metrics  # noqa: E402
from mcv.pipeline import process_video  # noqa: E402


def _pool(counts, m):
    c = counts.setdefault(m["event"], {"tp": 0, "fp": 0, "fn": 0})
    for k in c:
        c[k] += m[k]


def _rates(c):
    p = c["tp"] / (c["tp"] + c["fp"]) if c["tp"] + c["fp"] else 0.0
    r = c["tp"] / (c["tp"] + c["fn"]) if c["tp"] + c["fn"] else 0.0
    return {"precision": p, "recall": r, **c}


def run(clips, cfg, cams, weights, tracker, use_clahe=None, use_dwell=True, tag=None):
    tag = tag or tracker
    per_clip, event_counts, frames, seconds = [], {}, 0, 0.0
    for c in clips:
        video = Path(c["video"])
        out = ROOT / "outputs" / "eval" / tag / video.stem
        t0 = time.perf_counter()
        s = process_video(video, cfg, cams[c["camera"]], weights, out, tracker=tracker, use_clahe=use_clahe,
                          use_dwell=use_dwell, write_video=False)
        seconds += time.perf_counter() - t0
        frames += s["frames"] // s["frame_stride"]
        gt = video.with_name(video.stem + "_gt.txt")
        if gt.exists() and tracker != "none":
            per_clip.append(tracking_metrics(gt, out / "tracks_mot.txt"))
        ev = video.with_name(video.stem + "_events.csv")
        if ev.exists():   # event times restart at 0 in every clip, so match clip by clip and pool the counts
            gt_events = load_gt_events(ev)
            for kind in ("zone_entry", "loitering"):
                _pool(event_counts, event_metrics(s["events"], gt_events, kind))
    res = {"tracker": tracker, "clahe": use_clahe, "dwell_rule": use_dwell, "fps": frames / seconds if seconds else 0.0}
    if per_clip:
        n = len(per_clip)
        res.update({k: sum(m[k] for m in per_clip) / n for k in ("MOTA", "IDF1")})
        res["ID_switches"] = sum(m["ID_switches"] for m in per_clip)
    for kind, c in event_counts.items():
        res[kind] = _rates(c)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--clips", required=True)
    ap.add_argument("--weights", required=True)
    ap.add_argument("--trackers", nargs="+", default=["bytetrack", "deepsort"])
    args = ap.parse_args()
    cfg = load_config(args.config)
    cams = load_cameras(cfg["rules"]["cameras_file"])
    clips = json.load(open(args.clips, encoding="utf-8"))
    results = [run(clips, cfg, cams, args.weights, t) for t in args.trackers]
    out = ROOT / "results" / "tracking.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    for r in results:
        print(r)


if __name__ == "__main__":
    main()
