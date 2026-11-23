# Part 3: Computer vision

| File / folder | What it is |
|---|---|
| `detector.py` | YOLOv8 training and evaluation (precision, recall, mAP, FPS) |
| `tracking.py` | ByteTrack / DeepSORT tracking of detected vessels |
| `rules.py` | Restricted-zone entry and loitering rules |
| `scoring.py` | Vision score s_vision of each track |
| `geo.py` | Camera pixel → latitude/longitude (homography from ground-control points) |
| `preprocess.py` | CLAHE for low light, ROI mask, night/haze augmentation |
| `pipeline.py` | Full video pipeline: detect, track, apply rules, write the annotated video |
| `data.py` | Roboflow download, video-wise re-split, single "vessel" class |
| `metrics.py` | MOTA, IDF1, ID switches, event precision/recall |
| `config.py` | Loads `../config.yaml` |
| `cameras.json` | Camera ROI, restricted zones, ground-control points |
| `bytetrack_vessel.yaml` | Tracker settings for slow vessels |
| `scripts/` | prepare_data, resplit_by_video, train, evaluate_detector, train_baselines, run_video, eval_tracking, eval_fusion, ablation, make_demo_clip |
| `notebooks/train_on_colab.ipynb` | GPU training on Google Colab |
| `models/` | `vessel_yolov8s_best.pt` after training. Until then the website uses COCO-pretrained YOLOv8s (boat class). |
| `demo/` | Demo clip (Singapore Maritime Dataset, MVI_1486_VIS) and its cached analysis |
| `data/` | Dataset, on this PC only (not on GitHub) |

## Dataset
Singapore Maritime Dataset from Roboflow (YOLOv8 export), 6,350 frames from 63 videos.

- **Split by video:** the export is re-split so that no recording appears in two splits (43/10/10 videos).
- **Classes:** Boat, Ferry, Kayak, Sail boat, Speed boat and Vessel-ship become one class, "vessel". Buoy, Flying bird-plane and Other are dropped.

## Train (Colab, T4 GPU)
1. Open `notebooks/train_on_colab.ipynb` in Colab.
2. Choose Runtime → T4 GPU.
3. Run the cells. The notebook clones this repository, downloads the dataset from Roboflow, re-splits it, then trains and evaluates the model.
4. Put the resulting `vessel_yolov8s_best.pt` in `models/` and its `results/` folder here, then push.

Commands, run from the repository root:
```
python computer_vision/scripts/resplit_by_video.py --src <roboflow_export> --dst computer_vision/data/maritime
python computer_vision/scripts/prepare_data.py --root computer_vision/data/maritime --conditions-csv computer_vision/data/maritime/conditions.csv
python computer_vision/scripts/train.py --data computer_vision/data/maritime/data_vessel.yaml --weights yolov8s.pt --device 0
python computer_vision/scripts/evaluate_detector.py --weights computer_vision/models/vessel_yolov8s_best.pt --data computer_vision/data/maritime/data_vessel.yaml --device 0
```
Extra packages for training: `pip install -r computer_vision/requirements-train.txt`
