"""AIS branch: the LSTM autoencoder from AIS_WEBAPP, feature engineering from raw AIS, and per-vessel scoring.

Two CSV layouts are accepted:
  * raw AIS  – one row per report with MMSI, time, LAT, LON, SOG, COG (column names are matched loosely,
               e.g. the Marine Cadastre names MMSI, BaseDateTime, LAT, LON, SOG, COG, VesselName);
               the six model features are derived per vessel by `engineer_features`.
  * features – the AIS_WEBAPP format: the six feature columns only, treated as one trajectory (no map position).
"""
import math
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn

EARTH_R_NM = 3440.065

# Readable anomaly type for the feature that contributes most to the reconstruction error.
FEATURE_LABELS = {
    "SOG": "Abnormal speed",
    "COG": "Abnormal heading",
    "speed_change": "Sudden speed change",
    "course_change": "Erratic course changes",
    "distance_nm": "Position jump (possible spoofing)",
    "time_gap_min": "AIS transmission gap",
}

ALIASES = {
    "mmsi": ["mmsi"],
    "t": ["basedatetime", "timestamp", "# timestamp", "datetime", "time", "date_time", "base_date_time"],
    "lat": ["lat", "latitude"],
    "lon": ["lon", "long", "longitude", "lng"],
    "SOG": ["sog", "speed", "speed_over_ground"],
    "COG": ["cog", "course", "course_over_ground"],
    "name": ["vesselname", "vessel_name", "shipname", "ship_name", "name"],
    "type": ["vesseltype", "vessel_type", "ship_type", "shiptype"],
}


class LSTMAutoencoder(nn.Module):
    """Same architecture as AIS_WEBAPP/app.py, so the saved state_dict loads unchanged."""

    def __init__(self, n_features, hidden_dim=32, latent_dim=16, num_layers=1):
        super().__init__()
        self.encoder = nn.LSTM(input_size=n_features, hidden_size=hidden_dim, num_layers=num_layers, batch_first=True)
        self.encoder_to_latent = nn.Linear(hidden_dim, latent_dim)
        self.latent_to_decoder = nn.Linear(latent_dim, hidden_dim)
        self.decoder = nn.LSTM(input_size=hidden_dim, hidden_size=hidden_dim, num_layers=num_layers, batch_first=True)
        self.output_layer = nn.Linear(hidden_dim, n_features)

    def forward(self, x):
        _, seq_len, _ = x.shape
        _, (hidden, _) = self.encoder(x)
        latent = self.encoder_to_latent(hidden[-1])
        dec_in = self.latent_to_decoder(latent).unsqueeze(1).repeat(1, seq_len, 1)
        decoded, _ = self.decoder(dec_in)
        return self.output_layer(decoded)


class AisModel:
    def __init__(self, model_dir):
        model_dir = Path(model_dir)
        with open(model_dir / "metadata.pkl", "rb") as f:
            meta = pickle.load(f)
        with open(model_dir / "scaler.pkl", "rb") as f:
            self.scaler = pickle.load(f)
        self.features = list(meta["features"])
        self.window = int(meta["window_size"])
        self.threshold = float(meta["threshold"])
        self.net = LSTMAutoencoder(len(self.features), meta["hidden_dim"], meta["latent_dim"])
        self.net.load_state_dict(torch.load(model_dir / "lstm_autoencoder.pth", map_location="cpu"))
        self.net.eval()
        self.info = {"features": self.features, "window_size": self.window, "threshold": self.threshold,
                     "hidden_dim": meta["hidden_dim"], "latent_dim": meta["latent_dim"]}

    def score(self, X):
        """X: (n, n_features) rows of one trajectory. Returns (errors per window, per-feature errors per window)."""
        n = len(X)
        if n < self.window:
            return np.zeros(0), np.zeros((0, len(self.features)))
        Xs = self.scaler.transform(np.asarray(X, dtype=float)).astype(np.float32)
        wins = np.lib.stride_tricks.sliding_window_view(Xs, (self.window, Xs.shape[1]))[:, 0]
        errs, feat = [], []
        with torch.no_grad():
            for i in range(0, len(wins), 512):
                xb = torch.from_numpy(np.ascontiguousarray(wins[i:i + 512]))
                sq = (self.net(xb) - xb) ** 2
                errs.append(sq.mean(dim=(1, 2)).numpy())
                feat.append(sq.mean(dim=1).numpy())
        return np.concatenate(errs), np.concatenate(feat)


def _find(df, key):
    cols = {c.strip().lower(): c for c in df.columns}
    for alias in ALIASES[key]:
        if alias in cols:
            return cols[alias]
    return None


def haversine_nm(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_R_NM * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


SOG_SENTINELS = (102.2, 102.3)   # "speed not available" codes in AIS
MAX_SOG = 50.0                   # knots; faster reports are treated as glitches
MAX_SPEED_CHANGE = 20.0          # knots between two reports; larger jumps are treated as glitches
MIN_SOG_FOR_COURSE = 1.0         # below this the course over ground is noise


def engineer_features(g):
    """Model features for one vessel's reports sorted by time — the same steps as the training notebook (Ais.ipynb):

    1. SOG sentinels (102.2, 102.3) and SOG > 50 kn become missing;
    2. time_gap_min = minutes since the previous report, distance_nm = haversine distance from it,
       speed_change = SOG − previous SOG (missing when |Δ| > 20 kn),
       course_change = |ΔCOG| wrapped to [0, 180]° (missing when SOG < 1 kn, where COG is meaningless);
    3. missing deltas (incl. the first report) become 0; missing SOG/COG are filled forward then backward.
    """
    g = g.copy()
    sog = g["SOG"].astype(float)
    sog = sog.mask(sog.isin(SOG_SENTINELS) | (sog > MAX_SOG))
    cog = g["COG"].astype(float)

    g["time_gap_min"] = g["t"].diff() / 60.0
    g["distance_nm"] = pd.Series(haversine_nm(g["lat"].shift(), g["lon"].shift(), g["lat"], g["lon"]), index=g.index)
    sc = sog - sog.shift()
    g["speed_change"] = sc.mask(sc.abs() > MAX_SPEED_CHANGE)
    cc = (cog - cog.shift()).abs().clip(upper=360)
    cc = np.minimum(cc, 360 - cc)
    g["course_change"] = cc.mask(sog < MIN_SOG_FOR_COURSE)

    for c in ("speed_change", "course_change", "distance_nm", "time_gap_min"):
        g[c] = g[c].fillna(0.0)
    g["SOG"] = sog.ffill().bfill().fillna(0.0)
    g["COG"] = cog.ffill().bfill().fillna(0.0)
    return g


def _downsample(seq, n=300):
    if len(seq) <= n:
        return seq
    idx = np.linspace(0, len(seq) - 1, n).round().astype(int)
    return [seq[i] for i in idx]


def _vessel_result(model, mmsi, name, vtype, g):
    feats = g[model.features].astype(float).to_numpy()
    errs, ferrs = model.score(feats)
    has_pos = "lat" in g
    last = g.iloc[-1]
    res = {"mmsi": str(mmsi), "name": name or f"MMSI {mmsi}", "type": vtype, "n_reports": int(len(g)),
           "n_windows": int(len(errs))}
    if has_pos:
        res.update({"lat": round(float(last["lat"]), 6), "lon": round(float(last["lon"]), 6),
                    "sog": round(float(last["SOG"]), 2), "cog": round(float(last["COG"]), 1),
                    "first_t": float(g["t"].iloc[0]), "last_t": float(last["t"]),
                    "track": _downsample([[round(float(a), 6), round(float(b), 6)]
                                          for a, b in zip(g["lat"], g["lon"])])})
    if len(errs) == 0:
        res.update({"status": "insufficient", "max_error": None, "anomalous_windows": 0, "points": [],
                    "series": []})
        return res

    w = model.window
    end_rows = g.iloc[w - 1:]
    worst = int(np.argmax(errs))
    top = model.features[int(np.argmax(ferrs[worst]))]
    contrib = {f: round(float(v), 4) for f, v in zip(model.features, ferrs[worst])}
    n_anom = int((errs > model.threshold).sum())
    res.update({
        "status": "anomaly" if n_anom else "normal",
        "max_error": round(float(errs[worst]), 4),
        "anomalous_windows": n_anom,
        "worst_window": {"start_row": worst + 1, "end_row": worst + w, "top_feature": top,
                         "label": FEATURE_LABELS.get(top, top), "feature_errors": contrib},
        "anomaly_type": FEATURE_LABELS.get(top, top) if n_anom else None,
    })
    if has_pos:
        res["worst_window"].update({"t": float(end_rows["t"].iloc[worst]),
                                    "lat": round(float(end_rows["lat"].iloc[worst]), 6),
                                    "lon": round(float(end_rows["lon"].iloc[worst]), 6)})
        tops = [model.features[int(i)] for i in np.argmax(ferrs, axis=1)]
        res["points"] = [{"mmsi": str(mmsi), "name": res["name"], "t": float(t), "lat": float(la), "lon": float(lo),
                          "recon_error": float(e), "top_feature": tf}
                         for t, la, lo, e, tf in zip(end_rows["t"], end_rows["lat"], end_rows["lon"], errs, tops)]
        series_t = end_rows["t"].to_numpy()
    else:
        res["points"] = []
        series_t = np.arange(w, w + len(errs))
    res["series"] = _downsample([[float(t), round(float(e), 4)] for t, e in zip(series_t, errs)], 200)
    return res


def analyze_dataframe(df, model):
    """Scores every vessel in a raw-AIS or feature-only DataFrame."""
    df = df.copy()
    raw = all(_find(df, k) for k in ("mmsi", "t", "lat", "lon", "SOG", "COG"))
    if raw:
        rename = {_find(df, k): k for k in ("mmsi", "t", "lat", "lon", "SOG", "COG", "name", "type") if _find(df, k)}
        df = df.rename(columns=rename)
        t = df["t"]
        if pd.api.types.is_numeric_dtype(t):
            df["t"] = t.astype(float)
        else:
            dt = pd.to_datetime(t, utc=True, errors="coerce", format="mixed")
            df["t"] = (dt - pd.Timestamp(0, tz="UTC")).dt.total_seconds()
        df = df.dropna(subset=["t", "lat", "lon", "SOG", "COG"])
        df = df.sort_values(["mmsi", "t"])
        vessels = []
        for mmsi, g in df.groupby("mmsi", sort=False):
            g = engineer_features(g.reset_index(drop=True))
            name = str(g["name"].dropna().iloc[0]).strip() if "name" in g and g["name"].notna().any() else None
            vtype = str(g["type"].dropna().iloc[0]) if "type" in g and g["type"].notna().any() else None
            vessels.append(_vessel_result(model, mmsi, name, vtype, g))
        mode = "raw"
    else:
        missing = [f for f in model.features if f not in df.columns]
        if missing:
            raise ValueError("CSV needs either raw AIS columns (MMSI, time, LAT, LON, SOG, COG) or the model "
                             f"features {model.features}; missing: {missing}")
        vessels = [_vessel_result(model, "uploaded", "Uploaded trajectory", None, df.reset_index(drop=True))]
        mode = "features"

    vessels.sort(key=lambda v: -(v["max_error"] or 0))
    scored = [v for v in vessels if v["max_error"] is not None]
    return {
        "mode": mode,
        "threshold": model.threshold,
        "window_size": model.window,
        "n_vessels": len(vessels),
        "n_reports": int(sum(v["n_reports"] for v in vessels)),
        "n_windows": int(sum(v["n_windows"] for v in vessels)),
        "n_anomalous_vessels": sum(v["status"] == "anomaly" for v in vessels),
        "n_anomalous_windows": int(sum(v["anomalous_windows"] for v in scored)),
        "time_range": ([min(v["first_t"] for v in vessels), max(v["last_t"] for v in vessels)]
                       if mode == "raw" and vessels else None),
        "vessels": vessels,
    }


class QuantileScorer:
    """s_AIS from known quantiles of the error distribution on normal traffic (interpolated in log-error space).

    Used when the full array of validation errors is not stored; the quantiles printed by the training
    notebook are kept in models/ais/error_quantiles.json.
    """

    def __init__(self, quantiles):
        pts = sorted((float(e), float(q)) for e, q in quantiles)
        self.log_e = np.log10([max(e, 1e-12) for e, _ in pts])
        self.q = np.array([q for _, q in pts])

    def __call__(self, error):
        return float(np.interp(math.log10(max(float(error), 1e-12)), self.log_e, self.q))


def exp_tail_score(error, tau):
    """s_AIS when no validation errors are stored: treats τ as the 99th percentile of an exponential tail,
    so s = 1 − exp(−ln(100)·e/τ) gives 0.99 at e = τ and 0.999 at e = 1.5τ."""
    return 1.0 - math.exp(-math.log(100.0) * max(float(error), 0.0) / tau)
