"""Run the full vision branch on a video and write an annotated video, MOT tracks and summary.json.

    python scripts/run_video.py --video harbour.mp4 --weights models/vessel_yolov8s_best.pt --camera harbour_cam_1
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from computer_vision.config import ROOT, load_cameras, load_config  # noqa: E402
from computer_vision.pipeline import process_video  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--video", required=True)
    ap.add_argument("--weights", required=True)
    ap.add_argument("--camera", required=True, help="camera key in the cameras JSON")
    ap.add_argument("--tracker", default=None, choices=["bytetrack", "deepsort", "none"])
    ap.add_argument("--start-time", type=float, default=0.0, help="Unix time of the first frame (for AIS fusion)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    cfg = load_config(args.config)
    cam = load_cameras(cfg["rules"]["cameras_file"])[args.camera]
    out = Path(args.out) if args.out else ROOT / "outputs" / Path(args.video).stem
    s = process_video(args.video, cfg, cam, args.weights, out, tracker=args.tracker, start_time=args.start_time)
    flagged = [t for t in s["tracks"] if t["s_vision"] > 0]
    print(f"{len(s['tracks'])} tracks, {len(s['events'])} events, {len(flagged)} flagged vessels -> {out}")
    for t in flagged:
        print(f"  track {t['track_id']}: s_vision={t['s_vision']}  {'; '.join(t['reasons'])}")


if __name__ == "__main__":
    main()
