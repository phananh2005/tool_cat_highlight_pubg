from fastapi import FastAPI
from fastapi.responses import FileResponse
import uvicorn
# from core.match_detector import MatchDetector

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "ok"}

@app.get("/video")
def get_video(path: str):
    return FileResponse(path)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
