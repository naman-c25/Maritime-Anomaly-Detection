import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent          # repository root


def load_config(path=None):
    path = Path(path) if path else ROOT / "config.yaml"
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_cameras(path):
    path = Path(path)
    if not path.is_absolute():
        path = ROOT / path
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)["cameras"]


def resolve_path(p):
    p = Path(p)
    return p if p.is_absolute() else ROOT / p


def resolve_detector(cfg):
    """Weights used for inference: the fine-tuned vessel model when it exists, otherwise the COCO-pretrained
    fallback restricted to its boat class. Returns (weights, class_names or None, is_fallback)."""
    inf = cfg["inference"]
    trained = resolve_path(inf["weights"])
    if trained.exists():
        return str(trained), None, False
    return str(resolve_path(inf["fallback_weights"])), inf.get("fallback_classes"), True
