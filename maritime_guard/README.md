---
title: MaritimeGuard
emoji: 🚢
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# MaritimeGuard: AIS + camera maritime anomaly detection

One web app that combines:

- **AIS branch:** an LSTM autoencoder (trained in Ais.ipynb on Marine Cadastre AIS for New York harbour, Mar–Apr 2024, 1,250 vessels) scores sliding windows of 20 AIS reports per vessel. The reconstruction error above τ marks an anomaly, and the feature that contributes most explains it (speed, course, position jump, transmission gap).
- **Vision branch:** YOLOv8 detection, ByteTrack tracking, restricted-zone and loitering rules, then s_vision.
- **Fusion:** camera tracks are projected to lat/lon and matched one-to-one with AIS vessels within 150 m and 60 s.
  - The fused score is s_fused = α·s_AIS + (1−α)·s_vision.
  - A track with no AIS match is a dark vessel.

```
backend/    FastAPI service, models, demo data, training and evaluation scripts (see backend/README.md)
frontend/   React + Vite dashboard: Dashboard, Live Analysis, Vessel Tracking, Alerts, Analytics, Settings
Dockerfile  builds the frontend and serves it from the backend on port 7860 (Hugging Face Spaces)
```

## Run locally (Windows)

Backend (terminal 1):
```
cd backend
.venv\Scripts\activate
uvicorn api.app:app --port 8000
```
Frontend (terminal 2, for development with hot reload):
```
cd frontend
npm install
npm run dev            → http://localhost:5173
```
Or build the frontend once (`npm run build`) and open http://localhost:8000, since the backend serves `frontend/dist`.

With Docker: `docker build -t maritimeguard . && docker run -p 7860:7860 maritimeguard` → http://localhost:7860

## Demo scenario

On start-up the service loads a demo:

- **Camera clip:** MVI_1486_VIS from the Singapore Maritime Dataset test split, seen by an approximately calibrated "Marina South" camera with one restricted zone.
- **Simulated AIS file** (`backend/demo/ais_demo.csv`):
  - the ships visible in the clip transmit AIS from where the camera sees them, but the pilot boat does not;
  - 8 ships transit the Singapore Strait normally;
  - 3 ships behave abnormally: a transmission gap, a spoofed position jump, and erratic speed and course.

The AIS data are synthetic. The anomaly scores, detections and alerts shown are the real outputs of the models. Real data can be uploaded on the Live Analysis page.

## Deploy (Hugging Face Spaces + GitHub)

1. Create a Space on huggingface.co (SDK **Docker**, hardware CPU basic, which is free).
2. Create a GitHub repository and push this folder (Git LFS is needed for the model and video files):
   ```
   git init -b main
   git lfs install
   git add .
   git commit -m "MaritimeGuard"
   git remote add origin https://github.com/<you>/<repo>.git
   git push -u origin main
   ```
3. In GitHub, open the repository's Settings → Secrets and variables → Actions and add:
   - the secret `HF_TOKEN`, a Hugging Face token with write access;
   - the variable `HF_SPACE` = `<hf-username>/<space-name>`.
4. Every push to `main` now updates the Space (`.github/workflows/deploy-hf.yml`). The app is at `https://<hf-username>-<space-name>.hf.space`.

A free Space sleeps when unused, so open it a few minutes before a presentation.

### Updating the models later
| Change | What to do |
|---|---|
| Trained vessel detector | put `best.pt` at `backend/models/vessel_yolov8s_best.pt`, then push. The demo clip is re-analysed automatically. |
| Detector test results | put `results/detector_*.json` from `scripts/evaluate_detector.py` in `backend/results/`, then push. They appear on Analytics. |
| Retrained AIS model | replace the 3 files in `backend/models/ais/`, then push. |
| AIS error distribution | s_AIS uses the training-error percentiles from Ais.ipynb (`models/ais/error_quantiles.json`). For the exact percentile rank, save the errors in the notebook (`np.save("saved_model/validation_errors.npy", train_errors)`), copy the file to `backend/models/ais/`, then push. |
| Thresholds, α, zones, cameras | edit `backend/configs/*.yaml / *.json`, then push. |
