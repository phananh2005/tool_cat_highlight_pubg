from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn
import dataclasses
import traceback
import sys

from core.match_detector import detect_matches
from core.highlight_detector import detect_highlights
from core.models import Match

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
        highlights = detect_highlights(req.video_path, matches, req.player_name)
        return [dataclasses.asdict(h) for h in highlights]
    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
