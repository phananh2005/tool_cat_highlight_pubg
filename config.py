"""Config mặc định và load/save settings."""
from __future__ import annotations

import json
from pathlib import Path

DEFAULTS = {
    "frame_sample_interval": 2.0,       # seconds giữa mỗi lần sample frame
    "audio_spike_threshold": 0.8,       # 0-1, ngưỡng detect audio spike (RMS ratio)
    "template_match_threshold": 0.75,   # ngưỡng OpenCV template matching
    "scene_change_threshold": 30.0,     # ngưỡng mean abs diff giữa 2 frame liên tiếp
    "highlight_pad_before": 3.0,        # seconds pad trước highlight
    "highlight_pad_after": 2.0,         # seconds pad sau highlight
    "highlight_min_gap": 5.0,           # seconds — 2 highlight gần hơn thì merge
    "export_format": "mp4",
    "ffmpeg_path": "ffmpeg",
    "player_name": "",
    "kill_feed_region": [0.65, 0.0, 1.0, 0.35],  # x1,y1,x2,y2 tỷ lệ % crop kill feed
}

CONFIG_FILE = Path(__file__).parent / "settings.json"


def load_config() -> dict:
    """Load config, merge với defaults."""
    cfg = dict(DEFAULTS)
    if CONFIG_FILE.exists():
        try:
            user = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            cfg.update(user)
        except (json.JSONDecodeError, OSError):
            pass
    return cfg


def save_config(cfg: dict):
    """Lưu chỉ các giá trị khác default."""
    diff = {k: v for k, v in cfg.items() if DEFAULTS.get(k) != v}
    CONFIG_FILE.write_text(json.dumps(diff, indent=2, ensure_ascii=False), encoding="utf-8")
