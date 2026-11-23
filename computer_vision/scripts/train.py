"""Fine-tune YOLOv8 on the prepared vessel dataset (run from the repository root).

    python computer_vision/scripts/train.py --data computer_vision/data/maritime/data_vessel.yaml --weights yolov8s.pt
    # keep checkpoints somewhere safe (e.g. Google Drive) and continue after a disconnect:
    python computer_vision/scripts/train.py --data ... --project /content/drive/MyDrive/maritime_runs
    python computer_vision/scripts/train.py --resume /content/drive/MyDrive/maritime_runs/vessel_yolov8s/weights/last.pt

The best weights are copied to computer_vision/models/<run name>_best.pt (vessel_yolov8s_best.pt is what the
website uses).
"""
import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from computer_vision.config import ROOT, load_config  # noqa: E402
from computer_vision.detector import train  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--data", help="data_vessel.yaml (not needed with --resume)")
    ap.add_argument("--weights", default=None, help="yolov8n.pt / yolov8s.pt / yolov8m.pt")
    ap.add_argument("--epochs", type=int, default=None)
    ap.add_argument("--device", default=None)
    ap.add_argument("--project", default=None, help="folder for the training runs (absolute path recommended)")
    ap.add_argument("--resume", default=None, help="last.pt of an interrupted run to continue")
    args = ap.parse_args()

    if args.resume:
        from ultralytics import YOLO
        model = YOLO(args.resume)
        model.train(resume=True)
        best = Path(model.trainer.save_dir) / "weights" / "best.pt"
        name = Path(model.trainer.save_dir).name
    else:
        if not args.data:
            sys.exit("--data is required (or use --resume)")
        cfg = load_config(args.config)
        if args.weights:
            cfg["model"]["weights"] = args.weights
            cfg["train"]["name"] = f"vessel_{Path(args.weights).stem}"
        if args.epochs:
            cfg["train"]["epochs"] = args.epochs
        if args.device is not None:
            cfg["train"]["device"] = args.device
        project = Path(args.project) if args.project else ROOT / cfg["train"]["project"]
        cfg["train"]["project"] = str(project.resolve())
        best = train(cfg, Path(args.data).resolve())
        name = cfg["train"]["name"]

    dst = ROOT / "computer_vision" / "models" / f"{name}_best.pt"
    dst.parent.mkdir(exist_ok=True)
    shutil.copy(best, dst)
    print("best weights:", dst)


if __name__ == "__main__":
    main()
