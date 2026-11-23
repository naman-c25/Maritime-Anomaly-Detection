"""Writes the simulated AIS scenario used by the demo (demo/ais_demo.csv, Marine Cadastre column names).

Scenario around the demo camera at Marina South, Singapore, 08:00–10:05 UTC on the demo day:
  * the four large ships and the AIS aid-to-navigation buoy seen in demo/demo_clip.mp4 transmit AIS from the
    positions where the camera sees them (placed with the camera's homography), so they associate with their tracks;
  * the pilot boat in the clip does not transmit (it becomes a dark vessel for the fusion layer);
  * eight ships transit the Singapore Strait normally;
  * three ships behave abnormally: a 45-minute transmission gap with a jump, a spoofed position jump, and
    erratic speed/course changes (loitering with possible ship-to-ship transfer).
The data are synthetic; the anomaly scores the dashboard shows are the real outputs of the AIS model on them.
"""
import argparse
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from mcv.config import load_cameras, load_config  # noqa: E402
from mcv.geo import CameraProjection  # noqa: E402

NM_DEG = 1 / 60.0
rng = np.random.default_rng(7)

# (name, mmsi, type, ground pixel of the hull in the 1280x720 demo clip)
SCENE = [
    ("PACIFIC AURORA", 563012340, "Bulk Carrier", (441, 214)),
    ("RED HERON", 563098110, "Offshore Supply", (1135, 232)),
    ("MERIDIAN STAR", 477200310, "Tanker", (935, 187)),
    ("ORIENT GRACE", 566301220, "Container Ship", (10, 223)),
    ("SG PILOT BUOY 3", 995631003, "Aid to Navigation", (763, 489)),
]


def reports(t0, t1, step_lo=60, step_hi=180):
    t, out = t0, []
    while t <= t1:
        out.append(t)
        t += rng.uniform(step_lo, step_hi)
    return np.array(out)


# Approximate Singapore Strait traffic lanes (lat, lon): eastbound in the south, westbound in the north.
EAST = [(1.150, 103.55), (1.135, 103.74), (1.195, 103.85), (1.215, 103.95), (1.245, 104.05), (1.300, 104.20)]
WEST = list(reversed([(1.165, 103.55), (1.150, 103.74), (1.208, 103.85), (1.228, 103.95), (1.262, 104.05),
                      (1.315, 104.20)]))
FERRY = [(1.262, 103.82), (1.240, 103.83), (1.200, 103.87), (1.160, 103.91), (1.125, 103.95)]


def _seg_nm(a, b):
    dlat = (b[0] - a[0]) * 60
    dlon = (b[1] - a[1]) * 60 * math.cos(math.radians((a[0] + b[0]) / 2))
    return math.hypot(dlat, dlon)


def along(route, s_nm):
    """Position and course after s_nm nautical miles along a polyline route."""
    for a, b in zip(route, route[1:]):
        d = _seg_nm(a, b)
        if s_nm <= d or b == route[-1]:
            f = min(1.0, s_nm / d)
            lat, lon = a[0] + f * (b[0] - a[0]), a[1] + f * (b[1] - a[1])
            cog = math.degrees(math.atan2((b[1] - a[1]) * math.cos(math.radians(lat)), b[0] - a[0])) % 360
            return lat, lon, cog
        s_nm -= d


def moving(name, mmsi, vtype, route, start_nm, sog, t0, t1):
    rows, ts = [], reports(t0, t1)
    for t in ts:
        lat, lon, cog = along(route, start_nm + sog * (t - t0) / 3600)
        rows.append((mmsi, t, lat + rng.normal(0, 2e-5), lon + rng.normal(0, 2e-5),
                     max(0, sog + rng.normal(0, 0.2)), (cog + rng.normal(0, 1.0)) % 360, name, vtype))
    return rows


def anchored(name, mmsi, vtype, lat, lon, t0, t1, heading):
    rows = []
    # sparse reports earlier, then every 30 s around the camera clip so the space-time gate can match
    for t in np.concatenate([reports(t0, t1 - 600, 120, 360), np.arange(t1 - 600, t1 + 1, 30.0)]):
        rows.append((mmsi, t, lat + rng.normal(0, 1.5e-5), lon + rng.normal(0, 1.5e-5),
                     abs(rng.normal(0.1, 0.05)), (heading + rng.normal(0, 3)) % 360, name, vtype))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="demo/ais_demo.csv")
    args = ap.parse_args()
    cfg = load_config()
    cam = load_cameras(cfg["rules"]["cameras_file"])[cfg["demo"]["camera"]]
    proj = CameraProjection.from_camera(cam)
    clip_t = pd.Timestamp(cfg["demo"]["start_time"]).timestamp()
    t0, t1 = clip_t - 2 * 3600, clip_t + 300

    rows = []
    for name, mmsi, vtype, px in SCENE:
        lat, lon = proj.pixel_to_latlon(px)
        rows += anchored(name, mmsi, vtype, lat, lon, t0, t1, rng.uniform(0, 360))

    transit = [
        ("EVER HARMONY", 353100200, "Container Ship", EAST, 0.0, 14.0),
        ("SEA LOTUS", 563501230, "Bulk Carrier", EAST, 6.0, 12.2),
        ("KOTA MAJU", 533002210, "General Cargo", EAST, 14.0, 10.4),
        ("ATLAS VOYAGER", 538009120, "Bulk Carrier", EAST, 2.0, 13.3),
        ("NORDIC BREEZE", 257300400, "Tanker", WEST, 3.0, 11.5),
        ("GOLDEN CREST", 477601050, "Container Ship", WEST, 0.0, 15.1),
        ("STAR PIONEER", 636018700, "Tanker", WEST, 10.0, 12.8),
        ("CORAL WAVE", 548200900, "Passenger", FERRY, 0.0, 4.5),
    ]
    for name, mmsi, vtype, route, start, sog in transit:
        rows += moving(name, mmsi, vtype, route, start, sog, t0, t1)

    # 1) transmission gap: normal transit, silent for 45 minutes, reappears further along the lane
    r = moving("BLUE MARLIN 7", 412440150, "Fishing", EAST, 9.0, 11.0, t0, t1)
    gap_a, gap_b = clip_t - 75 * 60, clip_t - 30 * 60
    rows += [x for x in r if not gap_a < x[1] < gap_b]

    # 2) spoofed position: three reports 14 nm away, then back on track
    r = moving("KAPAL SETIA", 525017880, "Tanker", WEST, 6.0, 12.0, t0, t1)
    k = len(r) // 2
    for i in range(k, k + 3):
        m, t, la, lo, sp, c, n, vt = r[i]
        r[i] = (m, t, la + 0.15, lo + 0.18, sp + rng.uniform(15, 25), (c + 120) % 360, n, vt)
    rows += r

    # 3) erratic speed and course: drifting and zig-zagging in the anchorage (possible ship-to-ship transfer)
    lat, lon, t = 1.2420, 103.9050, t0
    for t in reports(t0, t1):
        sog = rng.choice([0.3, 1.0, 6.5, 9.0, 2.0])
        cog = rng.uniform(0, 360)
        lat += sog * 0.02 * NM_DEG * math.cos(math.radians(cog))
        lon += sog * 0.02 * NM_DEG * math.sin(math.radians(cog))
        rows.append((370442210, t, lat, lon, sog, cog, "OCEAN TRADER", "Tanker"))

    df = pd.DataFrame(rows, columns=["MMSI", "t", "LAT", "LON", "SOG", "COG", "VesselName", "VesselType"])
    df["BaseDateTime"] = pd.to_datetime(df["t"], unit="s", utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    df = df[["MMSI", "BaseDateTime", "LAT", "LON", "SOG", "COG", "VesselName", "VesselType"]]
    df["LAT"], df["LON"] = df["LAT"].round(6), df["LON"].round(6)
    df["SOG"], df["COG"] = df["SOG"].round(1), df["COG"].round(1)
    df.sort_values(["BaseDateTime", "MMSI"]).to_csv(args.out, index=False)
    print(f"{len(df)} reports, {df['MMSI'].nunique()} vessels -> {args.out}")


if __name__ == "__main__":
    main()
