"""Builds a short demo video from the consecutive frames of one Singapore Maritime Dataset recording.

    python scripts/make_demo_clip.py --images data/maritime/test/images --video MVI_1486_VIS --out demo/demo_clip.mp4
The Roboflow export keeps every 5th frame of the 30 fps recordings, so the clip plays at 6 fps in real time.
"""
import argparse
import re
import sys
import tempfile
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from computer_vision.pipeline import to_browser_mp4  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", required=True)
    ap.add_argument("--video", required=True, help="recording name, e.g. MVI_1486_VIS")
    ap.add_argument("--out", default="demo/demo_clip.mp4")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--fps", type=float, default=6.0)
    args = ap.parse_args()

    pat = re.compile(re.escape(args.video) + r"_frame(\d+)_")
    frames = sorted((int(m.group(1)), p) for p in Path(args.images).iterdir() if (m := pat.match(p.name)))
    frames = [p for _, p in frames if not p.stem.endswith(("_dark", "_haze"))]
    if not frames:
        sys.exit(f"no frames of {args.video} in {args.images}")
    first = cv2.imread(str(frames[0]))
    h, w = first.shape[:2]
    size = (args.width, int(round(h * args.width / w / 2)) * 2)
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "raw.mp4"
        vw = cv2.VideoWriter(str(raw), cv2.VideoWriter_fourcc(*"mp4v"), args.fps, size)
        for p in frames:
            vw.write(cv2.resize(cv2.imread(str(p)), size, interpolation=cv2.INTER_AREA))
        vw.release()
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        to_browser_mp4(raw, args.out)
    print(f"{len(frames)} frames, {size[0]}x{size[1]}, {len(frames) / args.fps:.1f} s -> {args.out}")


if __name__ == "__main__":
    main()
