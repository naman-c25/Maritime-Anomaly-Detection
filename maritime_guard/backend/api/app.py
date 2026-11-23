"""MaritimeGuard API: AIS anomaly detection, vision branch and AIS/vision fusion behind one service.

    uvicorn api.app:app --port 8000          (from backend/)

The built React frontend (frontend/dist, or ./static inside the Docker image) is served from "/" when present.
"""
import os
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
from fastapi import APIRouter, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from api.service import DEMO_CACHE, MEDIA, Service  # noqa: E402
from mcv.config import ROOT  # noqa: E402

VIDEO_EXT = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "200"))

svc = Service(os.environ.get("MCV_CONFIG"))
api = APIRouter(prefix="/api")


@api.get("/health")
def health():
    return {"status": "ok", "detector": svc.detector_info(), "ais_model": svc.ais_model.info,
            "cameras": list(svc.cameras), "s_ais_mapping": svc.scorer_kind}


@api.get("/state")
def state():
    return svc.snapshot()


@api.post("/demo/load")
def demo_load():
    job = svc.load_demo()
    return {"job": job, "state": svc.snapshot()}


@api.post("/demo/rebuild")
def demo_rebuild():
    return {"job": svc.rebuild_demo_cache()}


@api.get("/demo/ais.csv")
def demo_ais_csv():
    from mcv.config import resolve_path
    return FileResponse(resolve_path(svc.cfg["demo"]["ais_csv"]), media_type="text/csv", filename="ais_demo.csv")


@api.post("/ais/upload")
async def ais_upload(file: UploadFile = File(...)):
    data = await file.read()
    if len(data) > MAX_UPLOAD_MB * 1e6:
        raise HTTPException(413, f"file larger than {MAX_UPLOAD_MB} MB")
    import io
    try:
        svc.load_ais_csv(io.BytesIO(data), f"upload: {file.filename}")
    except (ValueError, KeyError, pd.errors.ParserError) as e:
        raise HTTPException(400, str(e))
    return svc.snapshot()


@api.post("/vision/upload")
async def vision_upload(file: UploadFile = File(...), camera: str = Form(None), start_time: str = Form(None)):
    camera = camera or svc.cfg["demo"]["camera"]
    if camera not in svc.cameras:
        raise HTTPException(400, f"unknown camera '{camera}'; known: {list(svc.cameras)}")
    data = await file.read()
    if len(data) > MAX_UPLOAD_MB * 1e6:
        raise HTTPException(413, f"file larger than {MAX_UPLOAD_MB} MB")
    suffix = Path(file.filename or "").suffix.lower()
    if suffix in VIDEO_EXT:
        if start_time:
            try:
                t0 = float(start_time)
            except ValueError:
                t0 = pd.Timestamp(start_time).timestamp()
        else:
            t0 = svc.default_start_time()
        tmp = Path(tempfile.mkdtemp()) / f"input{suffix}"
        tmp.write_bytes(data)
        return {"job": svc.submit_video(tmp, camera, t0, f"upload: {file.filename}")}
    if suffix in IMAGE_EXT:
        img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            raise HTTPException(400, "could not decode the image")
        return {"image": svc.analyse_image(img, camera)}
    raise HTTPException(400, f"unsupported file type '{suffix}'")


@api.get("/jobs/{job_id}")
def job(job_id: str):
    if job_id not in svc.jobs:
        raise HTTPException(404, "unknown job")
    return svc.jobs[job_id]


class SettingsIn(BaseModel):
    alpha: float | None = None
    levels: dict | None = None
    d_max_m: float | None = None
    dt_s: float | None = None


@api.put("/settings")
def put_settings(s: SettingsIn):
    if s.alpha is not None and not 0 <= s.alpha <= 1:
        raise HTTPException(400, "alpha must be in [0, 1]")
    svc.update_settings(s.alpha, s.levels, s.d_max_m, s.dt_s)
    return svc.snapshot()


class StatusIn(BaseModel):
    status: str


@api.patch("/alerts/{alert_id}")
def patch_alert(alert_id: str, body: StatusIn):
    if body.status not in ("Active", "Reviewing", "Resolved"):
        raise HTTPException(400, "status must be Active, Reviewing or Resolved")
    svc.set_alert_status(alert_id, body.status)
    return {"id": alert_id, "status": body.status}


@api.get("/media/{folder}/{name}")
def media(folder: str, name: str):
    base = DEMO_CACHE if folder == "demo" else MEDIA / folder
    path = (base / name).resolve()
    if base.resolve() not in path.parents or not path.exists():
        raise HTTPException(404, "not found")
    return FileResponse(path)


app = FastAPI(title="MaritimeGuard API")
app.add_middleware(CORSMiddleware, allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(api)


@app.on_event("startup")
def _startup():
    svc.load_demo()


# Single-page frontend (served when built): unknown paths fall back to index.html for client-side routing.
STATIC = Path(os.environ.get("FRONTEND_DIST", ROOT / "static"))
if not STATIC.exists():
    STATIC = ROOT.parent / "frontend" / "dist"
if STATIC.exists():
    app.mount("/assets", StaticFiles(directory=STATIC / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        f = (STATIC / path).resolve()
        if path and STATIC.resolve() in f.parents and f.is_file():
            return FileResponse(f)
        return FileResponse(STATIC / "index.html")
