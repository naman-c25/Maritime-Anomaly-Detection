"""Table 10: AIS only vs vision only vs fused score on labelled episodes, with the α sweep and alert-level calibration.

episodes.csv, one row per labelled episode (a vessel observed over a time window):
    episode_id,label,s_ais,s_vision
    ep001,1,0.998,0.91        label 1 = real anomaly (AIS gap, zone entry, loitering ...), 0 = ordinary passage
s_ais = percentile rank of the episode's largest AIS reconstruction error (1.0 when the vessel had no AIS),
s_vision = the track's s_vision from summary.json (0 when the vessel was not seen by a camera).

    python scripts/eval_fusion.py --episodes episodes.csv --days 14
"""
import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from mcv.config import ROOT, load_config  # noqa: E402
from mcv.fusion import alert_metrics, calibrate_levels, fused_score, sweep_alpha  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--episodes", required=True)
    ap.add_argument("--days", type=float, required=True, help="length of the observation period, for false alerts/day")
    ap.add_argument("--threshold", type=float, default=0.5, help="an episode is alerted when s_fused >= threshold")
    args = ap.parse_args()
    cfg = load_config(args.config)

    rows = list(csv.DictReader(open(args.episodes, newline="", encoding="utf-8")))
    y = [int(r["label"]) for r in rows]
    s_ais = [float(r["s_ais"]) for r in rows]
    s_vis = [float(r["s_vision"]) for r in rows]

    sweep = sweep_alpha(s_ais, s_vis, y, args.days, args.threshold)
    best = max(sweep, key=lambda r: (r["f1"], -r["false_alerts_per_day"]))
    table = {
        "AIS only (alpha=1)": alert_metrics(y, [s >= args.threshold for s in s_ais], args.days),
        "Vision only (alpha=0)": alert_metrics(y, [s >= args.threshold for s in s_vis], args.days),
        f"Fused (alpha={best['alpha']})": {k: v for k, v in best.items() if k != "alpha"},
    }
    normal = [fused_score(a, v, best["alpha"]) for a, v, l in zip(s_ais, s_vis, y) if l == 0]
    levels = calibrate_levels(normal) if len(normal) >= 20 else None

    out = ROOT / "results" / "fusion.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"episodes": len(rows), "threshold": args.threshold, "table": table, "sweep": sweep,
                               "best_alpha": best["alpha"], "levels": levels}, indent=2), encoding="utf-8")
    print(f"{'configuration':<24}{'P':>7}{'R':>7}{'F1':>7}{'false/day':>11}")
    for name, m in table.items():
        print(f"{name:<24}{m['precision']:7.3f}{m['recall']:7.3f}{m['f1']:7.3f}{m['false_alerts_per_day']:11.2f}")
    if levels:
        print("alert levels for configs/default.yaml (fusion.levels):", {k: round(v, 4) for k, v in levels.items()})
    else:
        print("fewer than 20 normal episodes: alert levels not recalibrated")
    print("saved", out)


if __name__ == "__main__":
    main()
