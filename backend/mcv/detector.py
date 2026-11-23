"""YOLOv8 training and evaluation (Sects. 3.3.2 and 5.2)."""
import time
from pathlib import Path

import yaml


def train(cfg, data_yaml):
    from ultralytics import YOLO
    t, m = cfg["train"], cfg["model"]
    model = YOLO(m["weights"])
    model.train(data=str(data_yaml), epochs=t["epochs"], imgsz=m["imgsz"], batch=t["batch"], device=t["device"],
                cos_lr=t["cos_lr"], patience=t["patience"], project=t["project"], name=t["name"], exist_ok=True,
                single_cls=True, **t.get("augment", {}))
    return Path(model.trainer.save_dir) / "weights" / "best.pt"


def evaluate(weights, data_yaml, split="test", imgsz=640, device="cpu", iou=0.45):
    """Precision, recall, mAP@0.5 and mAP@0.5:0.95 on one split (or on an image-list .txt given as `split`)."""
    from ultralytics import YOLO
    data_yaml = Path(data_yaml)
    if str(split).endswith(".txt"):          # evaluate on a condition subset by swapping the test entry
        meta = yaml.safe_load(open(data_yaml, encoding="utf-8"))
        meta["test"] = str(split)
        data_yaml = Path(split).with_suffix(".yaml")
        yaml.safe_dump(meta, open(data_yaml, "w", encoding="utf-8"))
        split = "test"
    r = YOLO(str(weights)).val(data=str(data_yaml), split=split, imgsz=imgsz, device=device, iou=iou,
                                  single_cls=True, plots=False, verbose=False)
    return {"precision": float(r.box.mp), "recall": float(r.box.mr),
            "mAP50": float(r.box.map50), "mAP50_95": float(r.box.map)}


def measure_fps(weights, image_paths, imgsz=640, device="cpu", conf=0.25, iou=0.45, warmup=10, limit=300):
    """Average end-to-end frames per second of detection (preprocess + inference + NMS) on real images."""
    import cv2
    from ultralytics import YOLO
    model = YOLO(str(weights))
    frames = [cv2.imread(str(p)) for p in list(image_paths)[:limit]]
    frames = [f for f in frames if f is not None]
    if not frames:
        raise ValueError("no readable images for the FPS measurement")
    for f in frames[:warmup]:
        model.predict(f, imgsz=imgsz, device=device, conf=conf, iou=iou, verbose=False)
    start = time.perf_counter()
    for f in frames:
        model.predict(f, imgsz=imgsz, device=device, conf=conf, iou=iou, verbose=False)
    return len(frames) / (time.perf_counter() - start)
