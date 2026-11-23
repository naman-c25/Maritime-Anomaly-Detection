"""Unit tests for the parts of the vision branch that do not need a trained detector."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fusion_api.fusion import AisScorer, alert_level, associate, build_alerts, calibrate_levels, fused_score, sweep_alpha  # noqa: E402
from computer_vision.geo import CameraProjection, haversine_m  # noqa: E402
from computer_vision.rules import TrackRules, point_in_polygon  # noqa: E402
from computer_vision.scoring import summarise_tracks  # noqa: E402

SQUARE = [[0, 0], [10, 0], [10, 10], [0, 10]]


def test_point_in_polygon():
    assert point_in_polygon((5, 5), SQUARE)
    assert not point_in_polygon((15, 5), SQUARE)
    assert not point_in_polygon((-1, -1), SQUARE)
    concave = [[0, 0], [10, 0], [10, 10], [5, 3], [0, 10]]
    assert not point_in_polygon((5, 8), concave)
    assert point_in_polygon((5, 2), concave)


def test_zone_entry_fires_once_per_entry():
    r = TrackRules([{"name": "berth", "polygon": SQUARE}], dwell_seconds=100, loiter_radius_px=1)
    assert r.update(1, (20, 5), 0.0) == []
    ev = r.update(1, (5, 5), 1.0)
    assert [e["type"] for e in ev] == ["zone_entry"]
    assert r.update(1, (6, 5), 2.0) == []          # still inside: no new event
    r.update(1, (20, 5), 3.0)                       # leaves
    assert [e["type"] for e in r.update(1, (5, 5), 4.0)] == ["zone_entry"]


def test_loitering_after_dwell_limit_and_reset_on_movement():
    r = TrackRules([], dwell_seconds=10, loiter_radius_px=5)
    for t in range(0, 10):
        assert r.update(7, (100, 100), float(t)) == []
    assert [e["type"] for e in r.update(7, (101, 100), 11.0)] == ["loitering"]

    moving = TrackRules([], dwell_seconds=10, loiter_radius_px=5)
    for t in range(0, 30):
        assert moving.update(8, (100 + 10 * t, 100), float(t)) == []
    assert not moving.tracks[8].loitering


def test_dwell_rule_can_be_disabled():
    r = TrackRules([], dwell_seconds=1, loiter_radius_px=5, use_dwell=False)
    for t in range(10):
        r.update(1, (0, 0), float(t))
    assert not r.tracks[1].loitering


def test_vision_score_uses_confidence_only_when_flagged():
    r = TrackRules([{"name": "berth", "polygon": SQUARE}], dwell_seconds=100, loiter_radius_px=1)
    r.update(1, (20, 20), 0.0, conf=0.8)
    r.update(2, (5, 5), 0.0, conf=0.9)
    r.update(2, (5, 6), 1.0, conf=0.7)
    s = {t["track_id"]: t for t in summarise_tracks(r)}
    assert s[1]["s_vision"] == 0.0
    assert s[2]["s_vision"] == pytest.approx(0.8)
    assert "restricted-zone entry (berth)" in s[2]["reasons"]


def test_homography_round_trip_and_haversine():
    latlon = [[40.6501, -74.0452], [40.6503, -74.0398], [40.6552, -74.0405], [40.6549, -74.0447]]
    pixel = [[100, 1000], [1800, 1000], [1500, 400], [300, 400]]
    proj = CameraProjection(pixel, latlon)
    for px, ll in zip(pixel, latlon):
        lat, lon = proj.pixel_to_latlon(px)
        assert haversine_m(lat, lon, *ll) < 0.5
    assert haversine_m(0, 0, 0, 1) == pytest.approx(111195, rel=1e-3)


def test_ais_scorer_and_fused_score():
    sc = AisScorer(list(range(100)))
    assert sc(-1) == 0.0
    assert sc(49.5) == pytest.approx(0.5)
    assert sc(1000) == 1.0
    assert fused_score(1.0, 0.0, 0.6) == pytest.approx(0.6)
    levels = {"advisory": 0.5, "warning": 0.8, "critical": 0.95}
    assert alert_level(0.96, levels) == "critical"
    assert alert_level(0.6, levels) == "advisory"
    assert alert_level(0.1, levels) is None
    lv = calibrate_levels([i / 1000 for i in range(1000)])
    assert lv["advisory"] < lv["warning"] < lv["critical"]


CFG = {"fusion": {"alpha": 0.6, "d_max_m": 150, "dt_s": 60, "ais_threshold": 2.3363,
                  "levels": {"advisory": 0.5, "warning": 0.8, "critical": 0.95}}}


def test_association_gate_and_alerts():
    vision = [{"track_id": 1, "lat": 40.6500, "lon": -74.0400, "last_t": 1000.0, "s_vision": 0.9,
               "reasons": ["restricted-zone entry (berth)"]},
              {"track_id": 2, "lat": 40.6600, "lon": -74.0300, "last_t": 1000.0, "s_vision": 0.85,
               "reasons": ["loitering (130 s)"]}]
    ais = [{"mmsi": 111, "t": 1010.0, "lat": 40.6505, "lon": -74.0401, "recon_error": 0.01},   # ~56 m from track 1
           {"mmsi": 222, "t": 1000.0, "lat": 40.7000, "lon": -74.1000, "recon_error": 482.24}]  # far away, anomalous
    pairs = associate(vision, ais, 150, 60)
    assert pairs[1][0]["mmsi"] == 111 and pairs[2] is None

    alerts = build_alerts(vision, ais, AisScorer([0.01 * i for i in range(300)]), CFG)
    by_src = {(a["source"], a["track_id"], a["mmsi"]): a for a in alerts}
    assert ("camera", 2, None) in by_src and "no AIS match" in by_src[("camera", 2, None)]["reason"]
    assert ("ais", None, 222) in by_src            # AIS anomaly outside the camera view is still reported
    assert all(a["s_fused"] >= 0.5 for a in alerts)


def _write_mot(path, rows):
    path.write_text("".join(f"{f},{i},{x},{y},{w},{h},1,1,1\n" for f, i, x, y, w, h in rows), encoding="utf-8")


def test_tracking_metrics_perfect_and_with_identity_switch(tmp_path):
    from computer_vision.metrics import tracking_metrics
    # two vessels moving right for 10 frames
    gt = [(f, gid, 10 * f + off, 50, 20, 10) for f in range(1, 11) for gid, off in ((1, 0), (2, 300))]
    _write_mot(tmp_path / "gt.txt", gt)
    _write_mot(tmp_path / "same.txt", gt)
    m = tracking_metrics(tmp_path / "gt.txt", tmp_path / "same.txt")
    assert m["MOTA"] == pytest.approx(100) and m["IDF1"] == pytest.approx(100) and m["ID_switches"] == 0

    # vessel 1 gets a new tracker ID from frame 6 on: one switch, IDF1 = 2*15/40 = 75 %
    switched = [(f, (9 if gid == 1 and f >= 6 else gid), x, y, w, h) for f, gid, x, y, w, h in gt]
    _write_mot(tmp_path / "sw.txt", switched)
    m = tracking_metrics(tmp_path / "gt.txt", tmp_path / "sw.txt")
    assert m["ID_switches"] == 1
    assert m["MOTA"] == pytest.approx(100 * (1 - 1 / 20))
    assert m["IDF1"] == pytest.approx(75.0)

    # tracker misses vessel 2 entirely: recall 50 %, MOTA 50 %
    _write_mot(tmp_path / "miss.txt", [r for r in gt if r[1] == 1])
    m = tracking_metrics(tmp_path / "gt.txt", tmp_path / "miss.txt")
    assert m["det_recall"] == pytest.approx(0.5) and m["MOTA"] == pytest.approx(50.0)


def test_event_metrics():
    from computer_vision.metrics import event_metrics
    gt = [{"type": "zone_entry", "start": 10, "end": 20}, {"type": "zone_entry", "start": 50, "end": 55}]
    pred = [{"type": "zone_entry", "t": 12}, {"type": "zone_entry", "t": 13}, {"type": "loitering", "t": 51}]
    m = event_metrics(pred, gt, "zone_entry", tolerance_s=0)
    assert (m["tp"], m["fp"], m["fn"]) == (1, 1, 1)


def test_alpha_sweep_prefers_fusion_when_sources_complement():
    # episodes 0-1 are seen only by AIS, 2-3 only by the camera, 4-5 are normal
    s_ais = [0.99, 0.98, 0.10, 0.20, 0.30, 0.10]
    s_vis = [0.00, 0.00, 0.95, 0.90, 0.00, 0.10]
    y = [1, 1, 1, 1, 0, 0]
    rows = {r["alpha"]: r for r in sweep_alpha(s_ais, s_vis, y, days=1, threshold=0.45)}
    assert rows[0.5]["f1"] > rows[1.0]["f1"] and rows[0.5]["f1"] > rows[0.0]["f1"]


def test_association_is_one_to_one():
    vision = [{"track_id": 1, "lat": 40.6500, "lon": -74.0400, "last_t": 0.0, "s_vision": 0.0},
              {"track_id": 2, "lat": 40.6502, "lon": -74.0400, "last_t": 0.0, "s_vision": 0.9,
               "zones_entered": ["berth"], "reasons": ["restricted-zone entry (berth)"]}]
    ais = [{"mmsi": 111, "t": 0.0, "lat": 40.6500, "lon": -74.0400, "recon_error": 0.01}]
    pairs = associate(vision, ais, 150, 60)
    assert pairs[1][0]["mmsi"] == 111 and pairs[2] is None      # the closer track gets the only AIS vessel
    alerts = build_alerts(vision, ais, AisScorer([0.01 * i for i in range(300)]), CFG)
    assert [a["track_id"] for a in alerts] == [2] and alerts[0]["type"] == "Dark vessel in restricted zone"
