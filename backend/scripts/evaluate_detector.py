"""Table 8: precision, recall, mAP@0.5, mAP@0.5:0.95 and FPS on the test split, overall and per condition.

    python scripts/evaluate_detector.py --weights models/vessel_yolov8s_best.pt --data data/maritime/data_vessel.yaml
"""
import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from mcv.config import ROOT, load_config  # noqa: E402
from mcv.data import images_in  # noqa: E402
from mcv.detector import evaluate, measure_fps  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--weights", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--device", default=None)
    args = ap.parse_args()
    cfg = load_config(args.config)
    device = args.device or cfg["inference"]["device"]
    imgsz, iou = cfg["model"]["imgsz"], cfg["inference"]["iou"]

    res = {"weights": args.weights, "device": device, "all": evaluate(args.weights, args.data, "test", imgsz, device, iou)}
    root = Path(yaml.safe_load(open(args.data, encoding="utf-8"))["path"])
    for lst in sorted(root.glob("test_*.txt")):
        res[lst.stem.replace("test_", "")] = evaluate(args.weights, args.data, str(lst), imgsz, device, iou)
    res["all"]["fps"] = measure_fps(args.weights, images_in(root / "test" / "images"), imgsz, device,
                                    cfg["inference"]["conf"], iou)

    out = ROOT / "results" / f"detector_{Path(args.weights).stem}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"{'subset':<10}{'P':>7}{'R':>7}{'mAP50':>8}{'mAP50-95':>10}")
    for k, v in res.items():
        if isinstance(v, dict):
            print(f"{k:<10}{v['precision']:7.3f}{v['recall']:7.3f}{v['mAP50']:8.3f}{v['mAP50_95']:10.3f}")
    print(f"FPS on {device}: {res['all']['fps']:.1f}   (saved to {out})")


if __name__ == "__main__":
    main()
