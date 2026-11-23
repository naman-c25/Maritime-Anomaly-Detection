"""Entry point for a Hugging Face Space (Gradio SDK, free CPU): starts the MaritimeGuard API + website on port 7860.

The Gradio SDK simply runs `python app.py`; the app itself is the FastAPI server in fusion_api/app.py, which also
serves the built frontend (frontend/dist, built by the GitHub deploy workflow). Locally you can run the same thing
with `python app.py` and open http://localhost:7860.
"""
import os

os.environ.setdefault("YOLO_CONFIG_DIR", "/tmp/Ultralytics")   # writable settings folder for Ultralytics

import uvicorn  # noqa: E402

from fusion_api.app import app  # noqa: E402

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "7860")))
