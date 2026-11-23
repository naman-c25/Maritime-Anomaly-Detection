# Part 2: AIS anomaly detection

| File | What it is |
|---|---|
| `Ais.ipynb` | Training notebook: cleaning, features, windows, LSTM autoencoder training, threshold τ |
| `models/lstm_autoencoder.pth` | Trained model weights |
| `models/scaler.pkl` | StandardScaler fitted on the training windows |
| `models/metadata.pkl` | Features, window size (20), threshold τ = 2.2987 (99th percentile of the training errors) |
| `models/error_quantiles.json` | Training-error percentiles printed by the notebook, used to turn an error into s_AIS |
| `ais_model.py` | The same model and the same feature steps as the notebook, used by the website |
| `streamlit_app.py` | The original standalone AIS app (AIS_WEBAPP) |
| `demo/ais_demo.csv` | Simulated AIS scenario for the demo (Singapore Strait) |
| `make_demo_ais.py` | Script that generates `demo/ais_demo.csv` |

## Data and model
- **Data:** Marine Cadastre AIS, New York harbour, 2 March – 28 April 2024, 9.4 M reports. 1,250 vessels have at least 50 reports.
- **Features per report:**
  - SOG, COG;
  - speed_change, with jumps over 20 kn removed;
  - course_change, wrapped to 0–180° and set to 0 when SOG < 1 kn;
  - distance_nm (haversine);
  - time_gap_min.
- **Windows:** 20 reports each, split at gaps over 60 min. The train/validation split is by vessel (80/20).
- **Model:** an LSTM autoencoder (32 hidden, 16 latent), trained for 30 epochs with MSE loss.
- **Result:** an anomaly is a window whose reconstruction error is above τ = 2.2987.

## Run alone
```
streamlit run ais_detection/streamlit_app.py
```
In the full website, upload a CSV on the **Live Analysis** page. Two formats work:
- raw AIS: `MMSI, BaseDateTime, LAT, LON, SOG, COG`;
- the six feature columns.
