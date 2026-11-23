"""Table 8 baselines: Faster R-CNN (ResNet-50 FPN) and SSD-MobileNet (SSDlite320-MobileNetV3) from torchvision,
trained and evaluated on the same YOLO-format vessel dataset.

    python scripts/train_baselines.py --data data/maritime/data_vessel.yaml --model fasterrcnn --epochs 30
    python scripts/train_baselines.py --data data/maritime/data_vessel.yaml --model ssd --epochs 60
"""
import argparse
import json
import sys
import time
from pathlib import Path

import cv2
import torch
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from computer_vision.config import ROOT  # noqa: E402
from computer_vision.data import images_in, label_for  # noqa: E402


class YoloFolder(torch.utils.data.Dataset):
    def __init__(self, image_dir):
        self.images = images_in(image_dir)

    def __len__(self):
        return len(self.images)

    def __getitem__(self, i):
        p = self.images[i]
        img = cv2.cvtColor(cv2.imread(str(p)), cv2.COLOR_BGR2RGB)
        h, w = img.shape[:2]
        boxes = []
        lab = label_for(p)
        if lab.exists():
            for line in lab.read_text(encoding="utf-8").splitlines():
                parts = line.split()
                if len(parts) >= 5:
                    xc, yc, bw, bh = map(float, parts[1:5])
                    boxes.append([(xc - bw / 2) * w, (yc - bh / 2) * h, (xc + bw / 2) * w, (yc + bh / 2) * h])
        boxes = torch.tensor(boxes, dtype=torch.float32).reshape(-1, 4)
        target = {"boxes": boxes, "labels": torch.ones(len(boxes), dtype=torch.int64)}
        return torch.from_numpy(img).permute(2, 0, 1).float() / 255.0, target


def build(kind):
    import torchvision
    if kind == "fasterrcnn":
        from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
        m = torchvision.models.detection.fasterrcnn_resnet50_fpn(weights="DEFAULT")
        m.roi_heads.box_predictor = FastRCNNPredictor(m.roi_heads.box_predictor.cls_score.in_features, 2)
        return m
    if kind == "ssd":
        return torchvision.models.detection.ssdlite320_mobilenet_v3_large(weights_backbone="DEFAULT", num_classes=2)
    raise ValueError(kind)


def collate(batch):
    return tuple(zip(*batch))


def box_iou(a, b):
    import torchvision
    return torchvision.ops.box_iou(a, b)


@torch.no_grad()
def evaluate(model, loader, device, conf=0.25):
    from torchmetrics.detection import MeanAveragePrecision
    model.eval()
    metric = MeanAveragePrecision(iou_type="bbox")
    tp = fp = fn = 0
    for imgs, targets in loader:
        outs = model([i.to(device) for i in imgs])
        outs = [{k: v.cpu() for k, v in o.items()} for o in outs]
        metric.update(outs, list(targets))
        for o, t in zip(outs, targets):   # precision/recall at IoU 0.5 for detections above `conf`
            pb = o["boxes"][o["scores"] >= conf]
            gb = t["boxes"]
            matched = set()
            if len(pb) and len(gb):
                ious = box_iou(pb, gb)
                for i in range(len(pb)):
                    j = int(ious[i].argmax())
                    if ious[i, j] >= 0.5 and j not in matched:
                        matched.add(j); tp += 1
                    else:
                        fp += 1
            else:
                fp += len(pb)
            fn += len(gb) - len(matched)
    m = metric.compute()
    return {"precision": tp / (tp + fp) if tp + fp else 0.0, "recall": tp / (tp + fn) if tp + fn else 0.0,
            "mAP50": float(m["map_50"]), "mAP50_95": float(m["map"])}


@torch.no_grad()
def fps(model, dataset, device, n=200):
    model.eval()
    imgs = [dataset[i][0].to(device) for i in range(min(n, len(dataset)))]
    for im in imgs[:5]:
        model([im])
    if device.type == "cuda":
        torch.cuda.synchronize()
    t0 = time.perf_counter()
    for im in imgs:
        model([im])
    if device.type == "cuda":
        torch.cuda.synchronize()
    return len(imgs) / (time.perf_counter() - t0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--model", choices=["fasterrcnn", "ssd"], required=True)
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--batch", type=int, default=4)
    ap.add_argument("--lr", type=float, default=0.01)
    args = ap.parse_args()
    meta = yaml.safe_load(open(args.data, encoding="utf-8"))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    train_ds, val_ds, test_ds = YoloFolder(meta["train"]), YoloFolder(meta["val"]), YoloFolder(meta["test"])
    train_dl = torch.utils.data.DataLoader(train_ds, args.batch, shuffle=True, collate_fn=collate, num_workers=2)
    val_dl = torch.utils.data.DataLoader(val_ds, args.batch, collate_fn=collate, num_workers=2)
    test_dl = torch.utils.data.DataLoader(test_ds, args.batch, collate_fn=collate, num_workers=2)

    model = build(args.model).to(device)
    params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.SGD(params, lr=args.lr, momentum=0.9, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=args.epochs)
    out_dir = ROOT / "computer_vision" / "models"; out_dir.mkdir(exist_ok=True)
    best, best_path = -1.0, out_dir / f"baseline_{args.model}_best.pt"

    for epoch in range(args.epochs):
        model.train()
        for imgs, targets in train_dl:
            imgs = [i.to(device) for i in imgs]
            targets = [{k: v.to(device) for k, v in t.items()} for t in targets]
            loss = sum(model(imgs, targets).values())
            opt.zero_grad(); loss.backward(); opt.step()
        sched.step()
        val = evaluate(model, val_dl, device)
        print(f"epoch {epoch + 1}/{args.epochs}  val mAP50={val['mAP50']:.3f}")
        if val["mAP50"] > best:
            best = val["mAP50"]
            torch.save(model.state_dict(), best_path)

    model.load_state_dict(torch.load(best_path, map_location=device))
    res = evaluate(model, test_dl, device)
    res["fps"] = fps(model, test_ds, device)
    res["device"] = str(device)
    out = ROOT / "computer_vision" / "results" / f"baseline_{args.model}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
