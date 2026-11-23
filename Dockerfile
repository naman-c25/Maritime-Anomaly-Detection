# One container: builds the React frontend and serves it, together with the AIS + computer-vision API,
# on port 7860 (the port Hugging Face Spaces expects). Build and run locally:
#   docker build -t maritimeguard . && docker run -p 7860:7860 maritimeguard

# 1) Frontend
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# 2) AIS detection + computer vision + fusion API
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 YOLO_CONFIG_DIR=/tmp/Ultralytics
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu \
    && pip install -r requirements.txt
COPY config.yaml ./
COPY ais_detection/ ./ais_detection/
COPY computer_vision/ ./computer_vision/
COPY fusion_api/ ./fusion_api/
COPY --from=web /web/dist ./frontend/dist
# COCO-pretrained fallback detector (used until computer_vision/models/vessel_yolov8s_best.pt is pushed)
RUN python -c "from ultralytics import YOLO; YOLO('computer_vision/models/yolov8s.pt')"
RUN useradd -m -u 1000 user && chown -R user:user /app
USER user
EXPOSE 7860
CMD ["uvicorn", "fusion_api.app:app", "--host", "0.0.0.0", "--port", "7860"]
