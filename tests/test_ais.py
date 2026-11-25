"""AIS branch: feature engineering from raw reports and scoring with the trained LSTM autoencoder."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ais_detection.ais_model import AisModel, QuantileScorer, analyze_dataframe, engineer_features, exp_tail_score  # noqa: E402
from computer_vision.config import ROOT  # noqa: E402

MODEL_DIR = ROOT / "ais_detection" / "models"


def test_engineer_features():
    g = pd.DataFrame({"t": [0.0, 60.0, 180.0], "lat": [1.0, 1.0, 1.0], "lon": [103.0, 103.01, 103.01],
                      "SOG": [10.0, 12.0, 11.0], "COG": [350.0, 10.0, 10.0]})
    f = engineer_features(g)
    assert f["speed_change"].tolist() == [0.0, 2.0, -1.0]
    assert f["course_change"].tolist() == [0.0, 20.0, 0.0]          # 350° → 10° is a 20° turn, not 340°
    assert f["time_gap_min"].tolist() == [0.0, 1.0, 2.0]
    assert f["distance_nm"].iloc[1] == pytest.approx(0.6, rel=0.01)   # 0.01° of longitude at 1° N ≈ 0.6 nm
    assert f["distance_nm"].iloc[2] == 0.0


def test_cleaning_matches_training_notebook():
    g = pd.DataFrame({"t": [0.0, 60, 120, 180, 240], "lat": [1.0] * 5, "lon": [103.0] * 5,
                      "SOG": [0.2, 102.3, 0.3, 30.0, 5.0], "COG": [10.0, 200.0, 90.0, 95.0, 100.0]})
    f = engineer_features(g)
    assert f["SOG"].tolist() == [0.2, 0.2, 0.3, 30.0, 5.0]            # sentinel 102.3 → missing → forward-filled
    assert f["speed_change"].tolist() == [0.0] * 5                    # missing SOG, +29.7 and −25 kn → 0
    # stationary (SOG < 1) → 0; like the notebook, a row whose SOG is missing keeps its course change (190° → 170°)
    assert f["course_change"].tolist() == [0.0, 170.0, 0.0, 5.0, 5.0]


def test_quantile_scorer():
    sc = QuantileScorer([[0.001, 0.0], [0.03, 0.5], [2.3, 0.99], [400, 1.0]])
    assert sc(2.3) == pytest.approx(0.99) and sc(1e-6) == 0.0 and sc(1e6) == 1.0
    assert sc(0.03) < sc(1.0) < sc(2.3)


def test_exp_tail_score():
    assert exp_tail_score(0, 2.0) == 0.0
    assert exp_tail_score(2.0, 2.0) == pytest.approx(0.99)
    assert exp_tail_score(3.0, 2.0) == pytest.approx(0.999)


@pytest.mark.skipif(not (MODEL_DIR / "lstm_autoencoder.pth").exists(), reason="AIS model not present")
def test_demo_scenario_scores():
    model = AisModel(MODEL_DIR)
    res = analyze_dataframe(pd.read_csv(ROOT / "ais_detection" / "demo" / "ais_demo.csv"), model)
    status = {v["name"]: v["status"] for v in res["vessels"]}
    assert res["mode"] == "raw" and res["n_vessels"] == 18
    assert {n for n, s in status.items() if s == "anomaly"} == {"KAPAL SETIA", "BLUE MARLIN 7", "OCEAN TRADER"}
    # the feature-only format of the AIS_WEBAPP gives the same score for the same trajectory
    v = next(v for v in res["vessels"] if v["name"] == "KAPAL SETIA")
    df = pd.read_csv(ROOT / "ais_detection" / "demo" / "ais_demo.csv")
    g = df[df.MMSI == 525017880].rename(columns={"LAT": "lat", "LON": "lon"})
    g["t"] = (pd.to_datetime(g.BaseDateTime, utc=True) - pd.Timestamp(0, tz="UTC")).dt.total_seconds()
    feats = engineer_features(g.sort_values("t").reset_index(drop=True))[model.features]
    single = analyze_dataframe(feats, model)
    assert single["mode"] == "features"
    assert single["vessels"][0]["max_error"] == pytest.approx(v["max_error"], rel=1e-4)
