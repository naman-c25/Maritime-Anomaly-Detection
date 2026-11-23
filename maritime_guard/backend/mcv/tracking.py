"""Multi-object tracking (Sect. 3.3.3): ByteTrack via Ultralytics, DeepSORT via deep-sort-realtime, or none."""
from dataclasses import dataclass
from itertools import count


@dataclass
class TrackedBox:
    track_id: int
    xyxy: tuple
    conf: float


def class_ids(model, class_names):
    if not class_names:
        return None
    wanted = {c.lower() for c in class_names}
    ids = [int(i) for i, n in model.names.items() if n.lower() in wanted]
    return ids or None


class VesselTracker:
    def __init__(self, weights, tracker="bytetrack", conf=0.25, iou=0.45, imgsz=640, device="cpu", deepsort_max_age=30,
                 class_names=None, bytetrack_cfg="bytetrack.yaml"):
        """`class_names` keeps only those classes (e.g. ["boat"] for a COCO-pretrained model); None keeps all."""
        from ultralytics import YOLO
        self.model = YOLO(str(weights))
        self.kind = tracker
        self.kw = dict(conf=conf, iou=iou, imgsz=imgsz, device=device, verbose=False,
                       classes=class_ids(self.model, class_names))
        self._ids = count(1)
        self.bytetrack_cfg = str(bytetrack_cfg)
        if tracker == "deepsort":
            from deep_sort_realtime.deepsort_tracker import DeepSort
            self.ds = DeepSort(max_age=deepsort_max_age)
        elif tracker not in ("bytetrack", "none"):
            raise ValueError(f"unknown tracker: {tracker}")

    def update(self, frame):
        if self.kind == "bytetrack":
            # detections down to ByteTrack's low threshold are needed for its second association stage
            kw = dict(self.kw, conf=min(self.kw["conf"], 0.1))
            r = self.model.track(frame, persist=True, tracker=self.bytetrack_cfg, **kw)[0]
            if r.boxes is None or r.boxes.id is None:
                return []
            return [TrackedBox(int(i), tuple(map(float, b)), float(c))
                    for b, i, c in zip(r.boxes.xyxy.tolist(), r.boxes.id.tolist(), r.boxes.conf.tolist())]

        r = self.model.predict(frame, **self.kw)[0]
        boxes = list(zip(r.boxes.xyxy.tolist(), r.boxes.conf.tolist()))
        if self.kind == "none":   # ablation: every detection gets a fresh identity, so nothing persists
            return [TrackedBox(next(self._ids), tuple(map(float, b)), float(c)) for b, c in boxes]

        dets = [([x1, y1, x2 - x1, y2 - y1], c, "vessel") for (x1, y1, x2, y2), c in boxes]
        out = []
        for t in self.ds.update_tracks(dets, frame=frame):
            if not t.is_confirmed() or t.time_since_update > 0:
                continue
            conf = t.get_det_conf()
            out.append(TrackedBox(int(t.track_id), tuple(map(float, t.to_ltrb())), float(conf if conf is not None else 0.0)))
        return out
