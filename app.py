"""Entry point for the Hugging Face Space (Gradio SDK). Locally: `python app.py` → http://localhost:7860

Free Gradio Spaces run on ZeroGPU hardware, which expects a Gradio server and at least one @spaces.GPU function.
So Gradio is started as the web server, and the MaritimeGuard API and website routes (fusion_api/app.py) are put in
front of Gradio's own routes. The models run on the CPU; the GPU probe below is never called, so no GPU quota is used.
"""
import os

os.environ.setdefault("YOLO_CONFIG_DIR", "/tmp/Ultralytics")   # writable settings folder for Ultralytics

try:                         # present on Hugging Face Spaces; must be imported before torch on ZeroGPU
    import spaces
except ImportError:
    spaces = None

import gradio as gr  # noqa: E402

from fusion_api.app import app as maritime_app, svc  # noqa: E402

if spaces is not None:
    @spaces.GPU(duration=5)
    def gpu_probe():
        """Required by ZeroGPU; not used (all models run on the CPU)."""
        return "ok"

with gr.Blocks(title="MaritimeGuard") as demo:
    gr.Markdown("MaritimeGuard API — open the site root for the dashboard.")

if __name__ == "__main__":
    svc.load_demo()
    demo.launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", "7860")), prevent_thread_lock=True,
                show_api=False)
    # MaritimeGuard's API and pages take precedence over Gradio's routes ("/" becomes the dashboard).
    demo.app.router.routes[0:0] = list(maritime_app.router.routes)
    demo.block_thread()
