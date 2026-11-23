"""Table 11: effect of CLAHE (night mAP), the tracker (IDF1, loitering) and the dwell-time rule (loitering events).

    python scripts/ablation.py --weights models/vessel_yolov8s_best.pt --data data/maritime/data_vessel.yaml --clips clips.json
The fused F1 column needs labelled episodes: rebuild episodes.csv from each variant's summary.json files
(outputs/eval/<variant>/...) and run scripts/eval_fusion.py on it.
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

import cv2
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from mcv.config import ROOT, load_cameras, load_config  # noqa: E402
from mcv.data import label_for  # noqa: E402
from mcv.detector import evaluate  # noqa: E402
from mcv.preprocess import apply_clahe  # noqa: E402
from scripts.eval_tracking import run  # noqa: E402


def night_with_and_without_clahe(weights, data_yaml, cfg, device):
    root = Path(yaml.safe_load(open(data_yaml, encoding="utf-8"))["path"])
    night_list = root / "test_night.txt"
    if not night_list.exists():
        return None
    imgsz, iou = cfg["model"]["imgsz"], cfg["inference"]["iou"]
    plain = evaluate(weights, data_yaml, str(night_list), imgsz, device, iou)

    work = ROOT / "outputs" / "ablation" / "night_clahe"
    (work / "images").mkdir(parents=True, exist_ok=True)
    (work / "labels").mkdir(parents=True, exist_ok=True)
    c = cfg["inference"]["clahe"]
    paths = []
    for p in map(Path, night_list.read_text(encoding="utf-8").split()):
        img = cv2.imread(str(p))
        if img is None:
            continue
        dst = work / "images" / p.name
        cv2.imwrite(str(dst), apply_clahe(img, c["clip_limit"], c["tile_grid"]))
        if label_for(p).exists():
            shutil.copy(label_for(p), work / "labels" / (p.stem + ".txt"))
        paths.append(str(dst))
    lst = work / "night_clahe.txt"
    lst.write_text("\n".join(paths) + "\n", encoding="utf-8")
    with_clahe = evaluate(weights, data_yaml, str(lst), imgsz, device, iou)
    return {"night_mAP50_with_clahe": with_clahe["mAP50"], "night_mAP50_without_clahe": plain["mAP50"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--weights", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--clips", default=None)
    ap.add_argument("--device", default=None)
    args = ap.parse_args()
    cfg = load_config(args.config)
    device = args.device or cfg["inference"]["device"]

    res = {"clahe": night_with_and_without_clahe(args.weights, args.data, cfg, device)}
    if args.clips:
        cams = load_cameras(cfg["rules"]["cameras_file"])
        clips = json.load(open(args.clips, encoding="utf-8"))
        res["full"] = run(clips, cfg, cams, args.weights, "bytetrack", tag="full")
        res["no_clahe"] = run(clips, cfg, cams, args.weights, "bytetrack", use_clahe=False, tag="no_clahe")
        res["no_tracking"] = run(clips, cfg, cams, args.weights, "none", tag="no_tracking")
        res["no_dwell"] = run(clips, cfg, cams, args.weights, "bytetrack", use_dwell=False, tag="no_dwell")
    out = ROOT / "results" / "ablation.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
