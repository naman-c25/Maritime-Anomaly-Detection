# Fusion API: connects AIS detection and computer vision to the website

| File | What it is |
|---|---|
| `fusion.py` | AIS ↔ camera matching (one-to-one, 150 m / 60 s), s_fused = α·s_AIS + (1−α)·s_vision, alert levels |
| `service.py` | Keeps the latest AIS analysis, video analysis and alerts, runs video jobs, loads the demo |
| `app.py` | FastAPI server: the REST API below, plus the built website |

Start it from the repository root: `uvicorn fusion_api.app:app --port 8000`

| Method | Path | Purpose |
|---|---|---|
| GET  | /api/health | which models are loaded |
| GET  | /api/state | everything the website shows |
| POST | /api/ais/upload | upload an AIS CSV |
| POST | /api/vision/upload | upload a video (background job) or an image |
| GET  | /api/jobs/{id} | progress of a video job |
| POST | /api/demo/load | reload the demo |
| PUT  | /api/settings | change α, alert levels, matching distance and time |
| PATCH| /api/alerts/{id} | set an alert to Active / Reviewing / Resolved |
