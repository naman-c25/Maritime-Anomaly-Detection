"""Download the Roboflow dataset, convert it to one 'vessel' class, add night/fog copies and tag test conditions.

    set ROBOFLOW_API_KEY=xxxx          (Windows)   |   export ROBOFLOW_API_KEY=xxxx   (Linux/Colab)
    python scripts/prepare_data.py --download
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from mcv.config import ROOT, load_config  # noqa: E402
from mcv.data import add_low_light_copies, download_roboflow, prepare_dataset, write_condition_lists  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--download", action="store_true", help="download from Roboflow (needs ROBOFLOW_API_KEY)")
    ap.add_argument("--root", default=None, help="existing dataset folder exported from Roboflow in YOLOv8 format")
    ap.add_argument("--conditions-csv", default=None, help="optional filename,condition list for the test split")
    args = ap.parse_args()
    cfg = load_config(args.config)

    if args.download:
        key = os.environ.get("ROBOFLOW_API_KEY")
        if not key:
            sys.exit("set the ROBOFLOW_API_KEY environment variable first")
        root = download_roboflow(cfg, key)
    else:
        root = Path(args.root) if args.root else ROOT / cfg["data"]["root"]
    if not (root / "data.yaml").exists():
        sys.exit(f"no data.yaml in {root}")

    data_yaml, stats = prepare_dataset(root, cfg["data"]["vessel_classes"], cfg["data"]["class_name"])
    print("original classes:", stats["original_classes"])
    print(f"kept {stats['kept_boxes']} vessel boxes, dropped {stats['dropped_boxes']} non-vessel boxes "
          f"in {stats['images']} label files")
    made = add_low_light_copies(root, cfg["data"]["low_light_fraction"])
    print(f"added {made} darkened/hazy training images")
    lists = write_condition_lists(root, "test", args.conditions_csv)
    print("test subsets:", {k: str(v) for k, v in lists.items()})
    (root / "prepare_report.json").write_text(json.dumps({"data_yaml": str(data_yaml), **stats, "low_light_copies": made,
                                                          "conditions": {k: str(v) for k, v in lists.items()}},
                                                         indent=2), encoding="utf-8")
    print("dataset ready:", data_yaml)


if __name__ == "__main__":
    main()
