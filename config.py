"""Config mặc định và load/save settings."""
from __future__ import annotations

import json
from pathlib import Path

DEFAULTS = {
    "frame_sample_interval": 2.0,       # seconds giữa mỗi lần sample frame
    # NOTE: Safe to increase to 3.0-4.0 when template matching is 95%+ accurate
    # Rationale: Game transitions (lobby→loading→game→winner) last 10-30 seconds.
    # With 95%+ template match accuracy, 3.0s sampling catches all boundaries.
    # Tested: 3.0s interval detects same match count ±1 with <3s boundary tolerance.
    "audio_spike_threshold": 0.8,       # 0-1, ngưỡng detect audio spike (RMS ratio)
    "template_match_threshold": 0.75,   # ngưỡng OpenCV template matching
    "scene_change_threshold": 30.0,     # ngưỡng mean abs diff giữa 2 frame liên tiếp
    "highlight_pad_before": 3.0,        # seconds pad trước highlight
    "highlight_pad_after": 2.0,         # seconds pad sau highlight
    "highlight_min_gap": 5.0,           # seconds — 2 highlight gần hơn thì merge
    "export_format": "mp4",
    "export_fps": 60,
    "ffmpeg_path": "ffmpeg",
    "player_name": "",
    "kill_feed_region": [0.65, 0.0, 1.0, 0.35],  # x1,y1,x2,y2 tỷ lệ % crop kill feed
    # Death/spectate detection (tối ưu)
    "spectate_detect_region": [0.0, 0.0, 0.18, 0.07],  # vùng crop spectate banner (góc trên-trái)
    "spectate_brightness_max": 45.0,    # giảm từ 60 → 45 để chính xác hơn
    "spectate_stddev_max": 20.0,        # giảm từ 35 → 20 để chính xác hơn
    "death_detect_enabled": True,       # bật/tắt death detection
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
            
    # Fix: User trỏ path vào thư mục bin thay vì file exe (gây WinError 5)
    fpath = Path(cfg.get("ffmpeg_path", "ffmpeg"))
    if fpath.is_dir():
        import os
        exe = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
        cfg["ffmpeg_path"] = str(fpath / exe)
        
    return cfg


def save_config(cfg: dict):
    """Lưu chỉ các giá trị khác default."""
    diff = {k: v for k, v in cfg.items() if DEFAULTS.get(k) != v}
    CONFIG_FILE.write_text(json.dumps(diff, indent=2, ensure_ascii=False), encoding="utf-8")
