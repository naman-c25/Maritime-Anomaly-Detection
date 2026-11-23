---
title: MaritimeGuard
emoji: 🚢
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# MaritimeGuard: AI-based maritime anomaly detection

The project has three parts, plus one small layer that connects them:

```
Maritime-Anomaly-Detection/
│
├── frontend/          PART 1 · Website (React + Vite dashboard)
│                      Dashboard, Live Analysis, Vessel Tracking map, Alerts, Analytics, Settings
│
├── ais_detection/     PART 2 · AIS anomaly detection
│                      Ais.ipynb (training notebook), LSTM autoencoder model, feature engineering,
│                      the original Streamlit app, demo AIS data
│
├── computer_vision/   PART 3 · Computer vision
│                      YOLOv8 vessel detection, ByteTrack tracking, restricted-zone / loitering rules,
│                      training scripts + Colab notebook, demo video
│
├── fusion_api/        CONNECTS 2 + 3 and serves 1
│                      combines the AIS score and the camera score into one alert (FastAPI server)
│
├── tests/             automatic tests for all parts
├── config.yaml        all settings (thresholds, α, model paths, demo)
├── requirements.txt   Python packages
└── Dockerfile         builds everything into one container for deployment
```

How it works:
```
 AIS CSV ──► ais_detection (LSTM) ──► s_AIS ───┐
                                                ├──► fusion_api ──► alerts ──► frontend (website)
 Video   ──► computer_vision (YOLOv8) ► s_vision┘
```
- **AIS:** every window of 20 AIS reports of a vessel is reconstructed by the LSTM autoencoder. An error above τ = 2.2987 marks an anomaly.
- **Camera:** vessels are detected and tracked. A track that enters a restricted zone or loiters gets s_vision > 0.
- **Fusion:** camera tracks are placed on the map and matched to AIS vessels within 150 m and 60 s.
  - The fused score is s_fused = α·s_AIS + (1−α)·s_vision, with α = 0.6.
  - A camera vessel with no AIS match is a "dark vessel".

## Run on your PC
```
cd F:\AI_ML
.venv\Scripts\activate
uvicorn fusion_api.app:app --port 8000
```
Open http://localhost:8000. After changing the frontend, run `npm run build` in `frontend/` once. For live editing, run `npm run dev` there and open http://localhost:5173.

Tests: `python -m pytest tests`

## Demo scenario
The website starts with a demo:

- **Camera:** a clip from the Singapore Maritime Dataset test split.
- **AIS:** a simulated AIS file for the Singapore Strait.
  - The ships in the clip transmit AIS, but the pilot boat does not (a dark vessel).
  - Three other ships behave abnormally.

The AIS data are synthetic. The scores and alerts are the real outputs of the models. Real data can be uploaded on the Live Analysis page.

## Deploy (GitHub → Hugging Face Space)
Every push to `main` is copied to the Hugging Face Space by `.github/workflows/deploy-hf.yml`, and the Space rebuilds the Docker image. One-time setup:

1. Create the Space (SDK **Docker**, CPU basic).
2. Create a Hugging Face token with write access.
3. In GitHub, open Settings → Secrets and variables → Actions and add:
   - the secret `HF_TOKEN`;
   - the variable `HF_SPACE` = `<hf-username>/<space-name>`.

| To update | Do this, then push |
|---|---|
| Vision model after training | copy `best.pt` to `computer_vision/models/vessel_yolov8s_best.pt` |
| Vision test results | `computer_vision/results/detector_*.json` (shown on Analytics) |
| AIS model | replace the files in `ais_detection/models/` |
| Settings, zones, cameras | `config.yaml`, `computer_vision/cameras.json` |
