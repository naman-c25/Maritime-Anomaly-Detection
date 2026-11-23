"""Fine-tune YOLOv8 on the prepared vessel dataset.

    python scripts/train.py --data data/maritime/data_vessel.yaml --weights yolov8s.pt
"""
import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from mcv.config import ROOT, load_config  # noqa: E402
from mcv.detector import train  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--data", required=True)
    ap.add_argument("--weights", default=None, help="yolov8n.pt / yolov8s.pt / yolov8m.pt")
    ap.add_argument("--epochs", type=int, default=None)
    ap.add_argument("--device", default=None)
    args = ap.parse_args()
    cfg = load_config(args.config)
    if args.weights:
        cfg["model"]["weights"] = args.weights
        cfg["train"]["name"] = f"vessel_{Path(args.weights).stem}"
    if args.epochs:
        cfg["train"]["epochs"] = args.epochs
    if args.device is not None:
        cfg["train"]["device"] = args.device
    best = train(cfg, args.data)
    dst = ROOT / "models" / f"{cfg['train']['name']}_best.pt"
    dst.parent.mkdir(exist_ok=True)
    shutil.copy(best, dst)
    print("best weights:", dst)


if __name__ == "__main__":
    main()
