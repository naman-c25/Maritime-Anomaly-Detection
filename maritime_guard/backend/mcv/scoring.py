"""Turns a track's rule flags into the vision anomaly score s_vision in [0, 1] and a readable reason."""
import numpy as np


def vision_score(state):
    """s_vision = mean detection confidence × 1[track entered a restricted zone or loitered]."""
    flagged = bool(state.zones_entered) or state.loitering
    conf = float(np.mean(state.confidences)) if state.confidences else 0.0
    return round(conf if flagged else 0.0, 4)


def vision_reasons(state):
    reasons = [f"restricted-zone entry ({z})" for z in sorted(state.zones_entered)]
    if state.loitering:
        reasons.append(f"loitering ({state.max_dwell:.0f} s)")
    return reasons


def summarise_tracks(rules, pixel_to_latlon=None):
    out = []
    for tid, st in rules.tracks.items():
        t, x, y = st.points[-1]
        item = {
            "track_id": int(tid),
            "first_t": round(st.first_t, 2),
            "last_t": round(st.last_t, 2),
            "n_detections": len(st.confidences),
            "mean_conf": round(float(np.mean(st.confidences)), 4),
            "last_ground_px": [round(x, 1), round(y, 1)],
            "zones_entered": sorted(st.zones_entered),
            "loitering": st.loitering,
            "max_dwell_s": round(st.max_dwell, 1),
            "s_vision": vision_score(st),
            "reasons": vision_reasons(st),
        }
        if pixel_to_latlon is not None:
            lat, lon = pixel_to_latlon((x, y))
            item["lat"], item["lon"] = round(lat, 6), round(lon, 6)
        out.append(item)
    return out
