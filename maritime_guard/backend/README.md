# Backend: AIS model, vision branch and fusion

`api/app.py` serves the whole system: the LSTM-autoencoder AIS model (`mcv/ais.py`), the YOLOv8 + ByteTrack vision
branch with restricted-zone and loitering rules (`mcv/pipeline.py`), and the AIS/vision fusion layer
(`mcv/fusion.py`). The scripts produce the evaluation numbers for the paper's tables.

```
api/app.py, api/service.py    REST API + in-memory state (latest AIS analysis, vision run, fused alerts, jobs)
configs/default.yaml          all settings (detector weights, thresholds, fusion α, gates, alert levels, demo)
configs/cameras.json          per-camera ROI, restricted zones and ground-control points
configs/bytetrack_vessel.yaml tracker settings for slow vessels
mcv/                          library: ais, data, preprocess, detector, tracking, rules, scoring, geo, fusion, metrics, pipeline
models/ais/                   AIS model from AIS_WEBAPP (lstm_autoencoder.pth, scaler.pkl, metadata.pkl)
models/vessel_yolov8s_best.pt fine-tuned vessel detector (after training; until then the COCO model is used)
demo/                         demo clip, simulated AIS scenario and the cached demo vision run
scripts/                      prepare_data, resplit_by_video, train, evaluate_detector, train_baselines, run_video,
                              eval_tracking, eval_fusion, ablation, make_demo_clip, make_demo_ais
notebooks/train_on_colab.ipynb  GPU training on Colab
tests/                        unit tests (rules, projection, fusion, AIS features and scoring)
```

## API
```
uvicorn api.app:app --port 8000
```
| Method | Path | Purpose |
|---|---|---|
| GET  | /api/health | models loaded, detector in use |
| GET  | /api/state | everything the dashboard shows (AIS vessels, camera tracks, alerts, settings) |
| POST | /api/ais/upload | CSV: raw AIS (MMSI, BaseDateTime, LAT, LON, SOG, COG) or the six model features |
| POST | /api/vision/upload | video (background job) or image; form fields `camera`, `start_time` |
| GET  | /api/jobs/{id} | progress of a video job |
| POST | /api/demo/load | reload the demo scenario |
| PUT  | /api/settings | change α, alert levels, association gate (alerts are recomputed) |
| PATCH| /api/alerts/{id} | set alert status Active / Reviewing / Resolved |

The demo vision run is cached in `demo/cache/`; its signature covers the detector weights and every setting it
depends on, so after a new `best.pt` is deployed the server re-analyses the demo clip once at start-up.

## 1. Install
```
python -m venv .venv
.venv\Scripts\activate            (Linux/Colab: source .venv/bin/activate)
pip install -r requirements-train.txt      (serving only: requirements.txt)
```
Training needs a GPU. Use `notebooks/train_on_colab.ipynb` (free T4) and run inference/the API on your PC.

## 2. Data (Roboflow, Singapore Maritime Dataset)
Download the Roboflow export in YOLOv8 format. Roboflow splits frames at random, so frames of one recording end up in
train and test; re-split by recording first, then convert to the single `vessel` class:
```
python scripts/resplit_by_video.py --src "path/to/roboflow_export" --dst data/maritime
python scripts/prepare_data.py --root data/maritime --conditions-csv data/maritime/conditions.csv
```
`data.vessel_classes` in `configs/default.yaml` lists the classes that count as vessels (buoys, birds and "Other" are
dropped). Darkened and hazy copies of 20% of the training images are added, and `test_visible.txt`, `test_nir.txt`,
`test_haze.txt` are written for the per-condition evaluation.

## 3. Train and evaluate the detector (Table 8)
```
python scripts/train.py --data data/maritime/data_vessel.yaml --weights yolov8s.pt
python scripts/evaluate_detector.py --weights models/vessel_yolov8s_best.pt --data data/maritime/data_vessel.yaml --device 0
python scripts/train_baselines.py --data data/maritime/data_vessel.yaml --model fasterrcnn
python scripts/train_baselines.py --data data/maritime/data_vessel.yaml --model ssd
```
Results go to `results/*.json`. Measure FPS on the device you report in the paper.

## 4. Cameras, zones and video
For each camera, copy an entry in `configs/cameras.json` and fill in:
- `frame_size`: the video size the pixel coordinates refer to (they are rescaled for other sizes);
- `roi`: polygon (pixels) of the water area to keep (or null);
- `restricted_zones`: named polygons (pixels) on the water;
- `gcp`: at least 4 points visible on the water/quay with their pixel position and real lat/lon (needed for fusion).
```
python scripts/run_video.py --video clip.mp4 --weights models/vessel_yolov8s_best.pt --camera harbour_cam_1 --start-time 1714000000
```
Output: `outputs/<clip>/annotated.mp4`, `tracks_mot.txt`, `summary.json` (tracks, events, `s_vision`, lat/lon).

## 5. Tracking and rule evaluation (Table 9, event P/R)
Annotate test clips in CVAT (export "MOT 1.1" → save as `<clip>_gt.txt`) and list events in `<clip>_events.csv`
(`type,start_s,end_s`, type = zone_entry or loitering). List the clips in `clips.json`:
`[{"video": "clips/cam1_a.mp4", "camera": "harbour_cam_1"}]`
```
python scripts/eval_tracking.py --clips clips.json --weights models/vessel_yolov8s_best.pt
python scripts/ablation.py --weights models/vessel_yolov8s_best.pt --data data/maritime/data_vessel.yaml --clips clips.json
```

## 6. Fusion with the AIS branch (Table 10)
The AIS branch provides, per scored window: `mmsi, t (Unix s), lat, lon, recon_error`, plus the array of validation
reconstruction errors saved as `validation_errors.npy` (used to turn an error into `s_AIS` by percentile rank).
Build `episodes.csv` (`episode_id,label,s_ais,s_vision`) for labelled episodes, then:
```
python scripts/eval_fusion.py --episodes episodes.csv --days 14
```
It sweeps α, reports AIS-only / vision-only / fused P, R, F1 and false alerts per day, and calibrates the alert levels.

## 7. Deploying a new detector
Copy the trained weights to `models/vessel_yolov8s_best.pt` (scripts/train.py does this), optionally add
`results/detector_vessel_yolov8s_best.json` from evaluate_detector.py (shown on the Analytics page), commit and push.
