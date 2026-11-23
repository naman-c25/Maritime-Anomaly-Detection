"""AIS/vision association, fused score (Eq. 11), alert levels and the α sweep of Sect. 5.3.

AIS input (from your AIS branch), one dict per scored window:
    {"mmsi": 366998410, "t": 1714000000.0, "lat": 40.65, "lon": -74.04, "recon_error": 3.1}
Vision input: the track summaries produced by mcv.pipeline (need "lat", "lon", "last_t", "s_vision", "reasons").
Times must share one clock (Unix seconds are easiest).
"""
import bisect

import numpy as np

from .geo import haversine_m


class AisScorer:
    """Maps a reconstruction error to [0, 1] by its percentile rank among the validation errors."""

    def __init__(self, validation_errors):
        self.sorted = np.sort(np.asarray(validation_errors, dtype=float))

    def __call__(self, error):
        return bisect.bisect_right(self.sorted, float(error)) / len(self.sorted)


def fused_score(s_ais, s_vision, alpha):
    return alpha * s_ais + (1.0 - alpha) * s_vision


def alert_level(score, levels):
    for name in ("critical", "warning", "advisory"):
        if score >= levels[name]:
            return name
    return None


def calibrate_levels(normal_scores):
    q = np.quantile(np.asarray(normal_scores, dtype=float), [0.95, 0.99, 0.999])
    return {"advisory": float(q[0]), "warning": float(q[1]), "critical": float(q[2])}


def associate(vision_tracks, ais_points, d_max_m, dt_s):
    """One-to-one association of vision tracks and AIS vessels inside the space-time gate.

    For every (track, vessel) pair the closest AIS report within dt_s and d_max_m is a candidate; candidates are
    then assigned greedily by distance so that a vessel (MMSI) explains at most one track. Returns
    {track_id: (ais_point, distance_m) or None}.
    """
    cands = []
    for tr in vision_tracks:
        if "lat" not in tr or tr.get("lat") is None:
            continue
        best = {}
        for a in ais_points:
            if abs(a["t"] - tr["last_t"]) > dt_s:
                continue
            d = haversine_m(tr["lat"], tr["lon"], a["lat"], a["lon"])
            if d <= d_max_m and (a["mmsi"] not in best or d < best[a["mmsi"]][1]):
                best[a["mmsi"]] = (a, d)
        cands += [(d, tr["track_id"], mmsi, a) for mmsi, (a, d) in best.items()]
    pairs = {tr["track_id"]: None for tr in vision_tracks}
    used = set()
    for d, tid, mmsi, a in sorted(cands, key=lambda c: c[0]):
        if pairs[tid] is None and mmsi not in used:
            pairs[tid] = (a, d)
            used.add(mmsi)
    return pairs


def _camera_alert_type(tr, matched, ais_anomaly):
    zone = bool(tr.get("zones_entered"))
    loiter = bool(tr.get("loitering"))
    if not matched:
        if zone:
            return "Dark vessel in restricted zone"
        if loiter:
            return "Dark vessel loitering"
        return "Unidentified vessel (no AIS)"
    if ais_anomaly:
        return "AIS anomaly confirmed by camera"
    if zone:
        return "Restricted-zone entry"
    if loiter:
        return "Loitering"
    return "Camera observation"


def build_alerts(vision_tracks, ais_points, ais_scorer, cfg, feature_labels=None):
    """Returns one alert per vessel whose fused score reaches at least the advisory level.

    `ais_scorer` maps a reconstruction error to s_AIS in [0, 1]. AIS points may carry "name" and "top_feature"
    (the feature with the largest reconstruction error), which make the alert text readable.
    """
    f = cfg["fusion"]
    alpha, levels, tau = f["alpha"], f["levels"], f["ais_threshold"]
    labels = feature_labels or {}
    pairs = associate(vision_tracks, ais_points, f["d_max_m"], f["dt_s"])
    alerts, matched_mmsi = [], set()

    for tr in vision_tracks:
        match = pairs.get(tr["track_id"])
        reasons = list(tr.get("reasons", []))
        a = None
        if match is None:
            s_ais, mmsi, name, ais_anom = 1.0, None, None, False
            reasons.append("no AIS match")
        else:
            a, dist = match
            mmsi, name = a["mmsi"], a.get("name")
            matched_mmsi.add(mmsi)
            s_ais = ais_scorer(a["recon_error"])
            ais_anom = a["recon_error"] > tau
            reasons.append(f"matched AIS {name or mmsi} at {dist:.0f} m")
            if ais_anom:
                reasons.append(f"AIS anomaly (error {a['recon_error']:.2f} > τ), confirmed visually")
        score = fused_score(s_ais, tr["s_vision"], alpha)
        level = alert_level(score, levels)
        if level:
            alerts.append({"source": "camera", "track_id": tr["track_id"], "mmsi": mmsi, "name": name,
                           "type": _camera_alert_type(tr, match is not None, ais_anom),
                           "s_ais": round(s_ais, 4), "s_vision": tr["s_vision"], "s_fused": round(score, 4),
                           "level": level, "t": tr.get("last_t"), "lat": tr.get("lat"), "lon": tr.get("lon"),
                           "reason": "; ".join(reasons)})

    # AIS anomalies outside the camera view still reach the operator, scored with s_vision = 0
    # (one alert per vessel, from its worst window).
    worst = {}
    for a in ais_points:
        if a["mmsi"] in matched_mmsi or a["recon_error"] <= tau:
            continue
        if a["mmsi"] not in worst or a["recon_error"] > worst[a["mmsi"]]["recon_error"]:
            worst[a["mmsi"]] = a
    for mmsi, a in worst.items():
        s_ais = ais_scorer(a["recon_error"])
        score = fused_score(s_ais, 0.0, alpha)
        level = alert_level(score, levels)
        if level:
            top = a.get("top_feature")
            alerts.append({"source": "ais", "track_id": None, "mmsi": mmsi, "name": a.get("name"),
                           "type": labels.get(top, "AIS behaviour anomaly"), "s_ais": round(s_ais, 4),
                           "s_vision": 0.0, "s_fused": round(score, 4), "level": level, "t": a.get("t"),
                           "lat": a["lat"], "lon": a["lon"],
                           "reason": f"AIS anomaly (error {a['recon_error']:.2f} > τ)"
                                     + (f", mainly {top}" if top else "") + ", outside camera view"})
    return sorted(alerts, key=lambda x: -x["s_fused"])


def alert_metrics(y_true, y_pred, days):
    y_true, y_pred = np.asarray(y_true, bool), np.asarray(y_pred, bool)
    tp = int((y_true & y_pred).sum()); fp = int((~y_true & y_pred).sum()); fn = int((y_true & ~y_pred).sum())
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    return {"precision": p, "recall": r, "f1": f1, "false_alerts_per_day": fp / days if days else float("nan"),
            "tp": tp, "fp": fp, "fn": fn}


def sweep_alpha(s_ais, s_vision, y_true, days, threshold, alphas=None):
    """Grid search of α on labelled episodes; an episode is alerted when s_fused >= threshold."""
    s_ais, s_vision = np.asarray(s_ais, float), np.asarray(s_vision, float)
    alphas = np.round(np.linspace(0, 1, 21), 2) if alphas is None else alphas
    rows = []
    for a in alphas:
        m = alert_metrics(y_true, fused_score(s_ais, s_vision, a) >= threshold, days)
        rows.append({"alpha": float(a), **m})
    return rows
