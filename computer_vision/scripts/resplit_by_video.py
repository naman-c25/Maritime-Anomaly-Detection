"""Re-split a Roboflow export of the Singapore Maritime Dataset by video (no recording shared between splits).

Roboflow splits frames at random, so frames of the same video end up in train, valid and test, which inflates
test accuracy. Run this on the extracted YOLOv8 export before prepare_data.py:

    python scripts/resplit_by_video.py --src "C:/Users/ASUS/Downloads/Singapore maritime.v1i.yolov8" --dst data/maritime
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from computer_vision.data import resplit_by_video  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="extracted Roboflow YOLOv8 export (contains data.yaml)")
    ap.add_argument("--dst", default="data/maritime")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    dst = Path(args.dst)
    if (dst / "data.yaml").exists():
        sys.exit(f"{dst} already contains a dataset; delete it first or choose another --dst")
    counts, split_of = resplit_by_video(args.src, dst, seed=args.seed)
    for s, c in counts.items():
        print(f"{s:6s} {c['videos']:3d} videos {c['images']:5d} images")
    (dst / "split_by_video.json").write_text(json.dumps(split_of, indent=2), encoding="utf-8")
    print(f"done -> {dst}  (video lists in split_by_video.json, test conditions in conditions.csv)")


if __name__ == "__main__":
    main()
