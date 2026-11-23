"""Roboflow download, single-class conversion, low-light augmentation and per-condition test lists."""
import csv
import shutil
from pathlib import Path

import cv2
import numpy as np
import yaml

from .config import ROOT
from .preprocess import add_haze, darken, guess_condition

SPLITS = {"train": "train", "val": "valid", "test": "test"}
IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp"}


def download_roboflow(cfg, api_key):
    from roboflow import Roboflow
    rc = cfg["data"]["roboflow"]
    location = ROOT / cfg["data"]["root"]
    project = Roboflow(api_key=api_key).workspace(rc["workspace"]).project(rc["project"])
    dataset = project.version(rc["version"]).download(rc["format"], location=str(location), overwrite=False)
    return Path(dataset.location)


def images_in(folder):
    return sorted(p for p in Path(folder).glob("*") if p.suffix.lower() in IMG_EXT)


def label_for(img_path):
    return img_path.parent.parent / "labels" / (img_path.stem + ".txt")


def prepare_dataset(root, vessel_classes=None, class_name="vessel"):
    """Rewrites labels to one 'vessel' class (keeping a backup) and writes data_vessel.yaml with absolute paths."""
    root = Path(root)
    meta = yaml.safe_load(open(root / "data.yaml", encoding="utf-8"))
    names = meta["names"] if isinstance(meta["names"], list) else [meta["names"][k] for k in sorted(meta["names"])]
    wanted = None if vessel_classes is None else {c.lower() for c in vessel_classes}
    keep_ids = {i for i, n in enumerate(names) if wanted is None or n.lower() in wanted}
    if wanted is not None and len(keep_ids) != len(wanted):
        missing = wanted - {names[i].lower() for i in keep_ids}
        raise ValueError(f"class names not found in data.yaml: {sorted(missing)}; available: {names}")

    stats = {"kept_boxes": 0, "dropped_boxes": 0, "images": 0}
    for split_dir in SPLITS.values():
        lab_dir = root / split_dir / "labels"
        if not lab_dir.exists():
            continue
        backup = root / split_dir / "labels_original"
        if not backup.exists():
            shutil.copytree(lab_dir, backup)
        for src in backup.glob("*.txt"):
            out_lines = []
            for line in src.read_text(encoding="utf-8").splitlines():
                parts = line.split()
                if len(parts) < 5:
                    continue
                if int(parts[0]) in keep_ids:
                    out_lines.append(" ".join(["0"] + parts[1:5]))
                    stats["kept_boxes"] += 1
                else:
                    stats["dropped_boxes"] += 1
            (lab_dir / src.name).write_text("\n".join(out_lines) + ("\n" if out_lines else ""), encoding="utf-8")
            stats["images"] += 1

    data_yaml = {"path": str(root), "names": [class_name], "nc": 1}
    for key, split_dir in SPLITS.items():
        if (root / split_dir / "images").exists():
            data_yaml[key] = str(root / split_dir / "images")
    out = root / "data_vessel.yaml"
    yaml.safe_dump(data_yaml, open(out, "w", encoding="utf-8"), sort_keys=False)
    stats["original_classes"] = names
    stats["vessel_class_ids"] = sorted(keep_ids)
    return out, stats


def video_id(filename, pattern=r"^(.*?)_frame\d+"):
    """Recording the frame came from, e.g. 'MVI_0790_VIS_OB_frame10_jpg.rf.x.jpg' -> 'MVI_0790_VIS_OB'."""
    import re
    m = re.match(pattern, filename)
    return m.group(1) if m else filename


def smd_condition(vid):
    """Singapore Maritime Dataset recording type from the video name."""
    if "Haze" in vid:
        return "haze"
    return "nir" if "_NIR" in vid else "visible"


def resplit_by_video(src_root, dst_root, ratios=(0.70, 0.15, 0.15), seed=0):
    """Re-splits a frame-level Roboflow export so that every recording lands in exactly one split.

    Videos are stratified by recording type (VIS / VIS_OB / NIR / *_Haze) and copied with their labels into
    dst_root in the same Roboflow layout. Also writes conditions.csv (filename,condition) for the test split.
    """
    src_root, dst_root = Path(src_root), Path(dst_root)
    frames = {}
    for split_dir in SPLITS.values():
        for img in images_in(src_root / split_dir / "images"):
            frames.setdefault(video_id(img.name), []).append(img)
    by_type = {}
    for vid in frames:
        by_type.setdefault(vid.split("_", 2)[-1] if vid.count("_") >= 2 else "other", []).append(vid)

    rng = np.random.default_rng(seed)
    assign = {}
    for kind, vids in sorted(by_type.items()):
        vids = sorted(vids)
        rng.shuffle(vids)
        n = len(vids)
        n_test = max(1, round(ratios[2] * n)) if n >= 3 else 0
        n_val = max(1, round(ratios[1] * n)) if n >= 3 else 0
        for i, v in enumerate(vids):
            assign[v] = "test" if i < n_test else ("valid" if i < n_test + n_val else "train")

    counts = {s: {"videos": 0, "images": 0} for s in ("train", "valid", "test")}
    rows = []
    for vid, imgs in frames.items():
        split = assign[vid]
        counts[split]["videos"] += 1
        for img in imgs:
            for kind in ("images", "labels"):
                (dst_root / split / kind).mkdir(parents=True, exist_ok=True)
            shutil.copy2(img, dst_root / split / "images" / img.name)
            lab = label_for(img)
            if lab.exists():
                shutil.copy2(lab, dst_root / split / "labels" / lab.name)
            counts[split]["images"] += 1
            if split == "test":
                rows.append((img.name, smd_condition(vid)))
    shutil.copy2(src_root / "data.yaml", dst_root / "data.yaml")
    with open(dst_root / "conditions.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["filename", "condition"])
        w.writerows(sorted(rows))
    split_of = {s: sorted(v for v, a in assign.items() if a == s) for s in ("train", "valid", "test")}
    return counts, split_of


def add_low_light_copies(root, fraction=0.2, seed=0):
    """Adds darkened and hazy copies (with identical labels) of a random subset of training images."""
    rng = np.random.default_rng(seed)
    img_dir = Path(root) / "train" / "images"
    originals = [p for p in images_in(img_dir) if not p.stem.endswith(("_dark", "_haze"))]
    chosen = rng.choice(len(originals), size=int(len(originals) * fraction), replace=False) if originals else []
    made = 0
    for i in chosen:
        src = originals[i]
        img = cv2.imread(str(src))
        if img is None:
            continue
        for tag, fn in (("_dark", darken), ("_haze", add_haze)):
            dst = src.with_name(src.stem + tag + src.suffix)
            if dst.exists():
                continue
            cv2.imwrite(str(dst), fn(img, rng))
            lab = label_for(src)
            if lab.exists():
                shutil.copy(lab, label_for(dst))
            made += 1
    return made


def write_condition_lists(root, split="test", conditions_csv=None):
    """Writes test_<condition>.txt image lists. Uses a CSV (filename,condition) if given, else a brightness/haze guess."""
    root = Path(root)
    imgs = images_in(root / SPLITS[split] / "images")
    given = {}
    if conditions_csv:
        with open(conditions_csv, newline="", encoding="utf-8") as f:
            given = {row["filename"]: row["condition"].strip().lower() for row in csv.DictReader(f)}
    groups = {}
    for p in imgs:
        cond = given.get(p.name)
        if cond is None:
            img = cv2.imread(str(p))
            cond = guess_condition(img) if img is not None else "day"
        groups.setdefault(cond, []).append(str(p))
    paths = {}
    for cond, items in groups.items():
        out = root / f"{split}_{cond}.txt"
        out.write_text("\n".join(items) + "\n", encoding="utf-8")
        paths[cond] = out
    return paths
