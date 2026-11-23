"""Restricted-zone entry (Eq. 9) and loitering (Eq. 10) rules applied to each vessel track."""
import math
from dataclasses import dataclass, field


def point_in_polygon(pt, polygon):
    """Ray casting: a point is inside when a horizontal ray from it crosses the boundary an odd number of times."""
    x, y = pt
    inside = False
    n = len(polygon)
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            x_cross = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < x_cross:
                inside = not inside
    return inside


@dataclass
class Zone:
    name: str
    polygon: list


@dataclass
class TrackState:
    first_t: float
    last_t: float
    anchor: tuple            # (x, y, t) where the current dwell period started
    zones_inside: set = field(default_factory=set)
    zones_entered: set = field(default_factory=set)
    loitering: bool = False
    max_dwell: float = 0.0
    confidences: list = field(default_factory=list)
    points: list = field(default_factory=list)   # (t, x, y) ground points


class TrackRules:
    """Keeps per-track state and emits zone-entry and loitering events."""

    def __init__(self, zones, dwell_seconds, loiter_radius_px, use_dwell=True):
        self.zones = [z if isinstance(z, Zone) else Zone(z["name"], z["polygon"]) for z in zones]
        self.dwell_seconds = dwell_seconds
        self.loiter_radius = loiter_radius_px
        self.use_dwell = use_dwell
        self.tracks = {}

    def update(self, track_id, ground_pt, t, conf=1.0):
        events = []
        st = self.tracks.get(track_id)
        if st is None:
            st = TrackState(first_t=t, last_t=t, anchor=(ground_pt[0], ground_pt[1], t))
            self.tracks[track_id] = st
        st.last_t = t
        st.confidences.append(float(conf))
        st.points.append((t, float(ground_pt[0]), float(ground_pt[1])))

        for zone in self.zones:
            inside = point_in_polygon(ground_pt, zone.polygon)
            if inside and zone.name not in st.zones_inside:
                st.zones_inside.add(zone.name)
                st.zones_entered.add(zone.name)
                events.append({"type": "zone_entry", "track_id": track_id, "zone": zone.name, "t": t})
            elif not inside:
                st.zones_inside.discard(zone.name)

        if self.use_dwell:
            ax, ay, at = st.anchor
            if math.hypot(ground_pt[0] - ax, ground_pt[1] - ay) > self.loiter_radius:
                st.anchor = (ground_pt[0], ground_pt[1], t)   # moved away: start a new dwell period
            else:
                dwell = t - at
                st.max_dwell = max(st.max_dwell, dwell)
                if dwell > self.dwell_seconds and not st.loitering:
                    st.loitering = True
                    events.append({"type": "loitering", "track_id": track_id, "t": t, "dwell_s": round(dwell, 1)})
        return events
