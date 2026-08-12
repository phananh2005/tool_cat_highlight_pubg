from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn
import dataclasses
import traceback
import sys

from core.match_detector import detect_matches
from core.highlight_detector import detect_highlights
from core.video_processor import export_highlights
from core.models import Match, Highlight

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DetectMatchRequest(BaseModel):
    video_path: str
    templates_dir: str = "templates"

class DetectHighlightRequest(BaseModel):
    video_path: str
    matches: list[dict]
    player_name: str = ""
    config: dict = None

class ExportRequest(BaseModel):
    video_path: str
    highlights: list[dict]
    output_dir: str = "exports"

_export_state = {
    "progress": 0.0,
    "message": "",
    "files": [],
    "done": False,
    "error": ""
}

@app.get("/")
def read_root():
    return {"status": "ok"}

@app.get("/video")
def get_video(path: str):
    return FileResponse(path)

@app.post("/api/detect/matches")
def api_detect_matches(req: DetectMatchRequest):
    try:
        matches = detect_matches(req.video_path, req.templates_dir)
        return [dataclasses.asdict(m) for m in matches]
    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}

@app.post("/api/detect/highlights")
def api_detect_highlights(req: DetectHighlightRequest):
    try:
        matches = [Match(**m) for m in req.matches]
        highlights = detect_highlights(req.video_path, matches, req.player_name, req.config)
        return [dataclasses.asdict(h) for h in highlights]
    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}

def run_export_bg(video_path: str, highlights: list, output_dir: str):
    global _export_state
    _export_state.update({"progress": 0.0, "message": "Đang bắt đầu export...", "files": [], "done": False, "error": ""})

    def progress_cb(prog: float, msg: str):
        _export_state["progress"] = prog
        _export_state["message"] = msg

    try:
        created = export_highlights(video_path, highlights, output_dir, progress_cb=progress_cb)
        _export_state["files"] = created
        _export_state["progress"] = 1.0
        _export_state["message"] = "Export thành công!"
    except Exception as e:
        traceback.print_exc()
        _export_state["error"] = str(e)
    finally:
        _export_state["done"] = True

@app.post("/api/export")
def api_export(req: ExportRequest, background_tasks: BackgroundTasks):
    try:
        highlights = [Highlight(**h) for h in req.highlights]
        background_tasks.add_task(run_export_bg, req.video_path, highlights, req.output_dir)
        return {"status": "started"}
    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}

@app.get("/api/export/status")
def api_export_status():
    return _export_state

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
