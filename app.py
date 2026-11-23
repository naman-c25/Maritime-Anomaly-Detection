"""Entry point for the Hugging Face Space (Gradio SDK). Locally: `python app.py` → http://localhost:7860

Free Gradio Spaces run on ZeroGPU hardware, which expects a Gradio server and at least one @spaces.GPU function.
Gradio is therefore the web server, and the MaritimeGuard API and website routes (fusion_api/app.py) are inserted
in front of Gradio's own routes whenever Gradio builds its web app — however the platform starts it. The models run
on the CPU; the GPU probe below is never called, so no GPU quota is used.
"""
import os

os.environ.setdefault("YOLO_CONFIG_DIR", "/tmp/Ultralytics")   # writable settings folder for Ultralytics

try:                         # present on Hugging Face Spaces; must be imported before torch on ZeroGPU
    import spaces
except ImportError:
    spaces = None

import gradio as gr  # noqa: E402
from gradio import routes as gradio_routes  # noqa: E402

from fusion_api.app import app as maritime_app, svc  # noqa: E402

_original_create_app = gradio_routes.App.create_app
DIAG = {"main": False, "create_app_calls": 0, "pid": os.getpid()}
_APPS = []


def _create_app_with_maritime_routes(*args, **kwargs):
    app = _original_create_app(*args, **kwargs)
    DIAG["create_app_calls"] += 1
    _APPS.append(app)
    # MaritimeGuard's API and pages take precedence over Gradio's routes ("/" becomes the dashboard)
    app.router.routes[0:0] = list(maritime_app.router.routes)
    return app


gradio_routes.App.create_app = staticmethod(_create_app_with_maritime_routes)

if spaces is not None:
    @spaces.GPU(duration=5)
    def gpu_probe():
        """Required by ZeroGPU; not used (all models run on the CPU)."""
        return "ok"


def diagnostics():
    import sys
    info = dict(DIAG, now_pid=os.getpid(), gradio=gr.__version__, argv=sys.argv,
                spaces=bool(spaces), env={k: v for k, v in os.environ.items() if "GRADIO" in k or "SPACE" in k.upper()
                                          and "TOKEN" not in k.upper()})
    if _APPS:
        info["routes_first"] = [getattr(r, "path", str(r)) for r in _APPS[-1].router.routes[:8]]
        info["middleware"] = [str(m) for m in _APPS[-1].user_middleware]
    return str(info)


with gr.Blocks(title="MaritimeGuard API") as demo:
    gr.Markdown("MaritimeGuard API — open the site root for the dashboard.")
    out = gr.Textbox()
    gr.Button("diag").click(diagnostics, None, out, api_name="diag")

svc.load_demo()     # demo AIS + cached demo video analysis

if __name__ == "__main__":
    DIAG["main"] = True
    demo.launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", "7860")), show_api=False)
