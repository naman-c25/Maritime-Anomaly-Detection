"""Image-to-map projection for fixed cameras and great-circle distance.

A plane homography is fitted from ground control points (pixel ↔ lat/lon) on the water surface, so a track's
waterline point can be compared with AIS positions in the fusion layer.
"""
import math

import numpy as np

EARTH_R = 6371008.8


def haversine_m(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dlmb = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_R * math.asin(math.sqrt(a))


def _fit_homography(src, dst):
    """Direct linear transform for >= 4 point pairs."""
    rows = []
    for (x, y), (u, v) in zip(src, dst):
        rows.append([-x, -y, -1, 0, 0, 0, u * x, u * y, u])
        rows.append([0, 0, 0, -x, -y, -1, v * x, v * y, v])
    _, _, vt = np.linalg.svd(np.asarray(rows, dtype=float))
    h = vt[-1].reshape(3, 3)
    return h / h[2, 2]


class CameraProjection:
    def __init__(self, pixel_pts, latlon_pts):
        if len(pixel_pts) < 4 or len(pixel_pts) != len(latlon_pts):
            raise ValueError("need at least 4 matching ground control points")
        self.lat0 = float(np.mean([p[0] for p in latlon_pts]))
        self.lon0 = float(np.mean([p[1] for p in latlon_pts]))
        metres = [self._to_local(lat, lon) for lat, lon in latlon_pts]
        self.H = _fit_homography(pixel_pts, metres)

    def _to_local(self, lat, lon):
        x = math.radians(lon - self.lon0) * EARTH_R * math.cos(math.radians(self.lat0))
        y = math.radians(lat - self.lat0) * EARTH_R
        return x, y

    def _from_local(self, x, y):
        lat = self.lat0 + math.degrees(y / EARTH_R)
        lon = self.lon0 + math.degrees(x / (EARTH_R * math.cos(math.radians(self.lat0))))
        return lat, lon

    def pixel_to_latlon(self, pt):
        u, v, w = self.H @ np.array([pt[0], pt[1], 1.0])
        return self._from_local(u / w, v / w)

    @classmethod
    def from_camera(cls, cam_cfg):
        gcp = cam_cfg.get("gcp")
        if not gcp:
            return None
        return cls(gcp["pixel"], gcp["latlon"])
