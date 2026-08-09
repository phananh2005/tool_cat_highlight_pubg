# Project Structure

```
tool_cat_highlight_yt/
│
├── 📄 Main Files
│   ├── main.py                    # Entry point - starts GUI
│   ├── config.py                  # Config defaults + load/save
│   ├── requirements.txt           # Python dependencies
│   ├── settings.json              # User settings (auto-generated)
│   └── .gitignore                 # Git ignore rules
│
├── 📚 Documentation (Main 3 files)
│   ├── README.md                  # User guide - installation & usage
│   ├── CONTRIBUTING.md            # Dev guide - optimization details
│   └── DEPLOYMENT.md              # QA guide - testing & deployment
│
├── 🎯 Core Logic (Detection & Export)
│   └── core/
│       ├── __init__.py
│       ├── models.py              # Data models (Match, Highlight, Project)
│       ├── match_detector.py      # Detect game boundaries (template matching)
│       ├── highlight_detector.py  # Detect highlights (audio + scene + OCR)
│       └── video_processor.py     # Cut/merge video clips (FFmpeg wrapper)
│
├── 🖥️  GUI (User Interface)
│   └── gui/
│       ├── __init__.py
│       ├── main_window.py         # Main window, video player, controls
│       └── timeline_widget.py     # Timeline visualization
│
├── 🖼️  Templates (Reference Images for Match Detection)
│   └── templates/
│       ├── README.md              # How to create templates
│       ├── lobby.png              # (optional - user provides)
│       ├── loading.png            # (optional - user provides)
│       ├── winner.png             # (optional - user provides)
│       ├── winner1.png
│       ├── winner2.png
│       └── winner3.png
│
└── 🔧 Setup Scripts (Windows)
    ├── setup.ps1                  # PowerShell setup script
    └── install_packages.bat       # Batch installer
```

---

## 📖 File Descriptions

### Documentation

| File | Audience | Purpose |
|------|----------|---------|
| **README.md** | Users | Installation, usage, settings, troubleshooting |
| **CONTRIBUTING.md** | Developers | v2.0 optimization details, architecture, tuning |
| **DEPLOYMENT.md** | QA/Testers | Testing procedures, checklist, rollback plan |

### Core Modules

| File | Purpose |
|------|---------|
| **main.py** | PyQt6 app entry point |
| **config.py** | Settings management (defaults + user overrides) |
| **models.py** | Match, Highlight, Project dataclasses |
| **match_detector.py** | Game boundary detection via template matching |
| **highlight_detector.py** | Multi-signal highlight detection (audio+scene+OCR) |
| **video_processor.py** | FFmpeg subprocess wrapper for cut/merge |

### GUI Modules

| File | Purpose |
|------|---------|
| **main_window.py** | Main window, video player, timeline, controls, dialogs |
| **timeline_widget.py** | Timeline visualization (matches + highlights) |

---

## 🔄 Data Flow

```
Input Video (MP4/MKV)
    ↓
match_detector.py
├─ Load templates (lobby.png, loading.png, winner.png)
├─ Sample frames every N seconds
├─ Template matching on each frame
├─ Cluster transitions
└─ Output: list[Match]
    ↓
highlight_detector.py (Parallel: Audio + Scene + Spectate)
├─ Audio spike detection (NumPy vectorized)
├─ Scene change detection (early resize)
├─ Spectate intervals (brightness/stddev)
├─ Kill feed OCR (optional, reduced sampling)
└─ Output: list[Highlight]
    ↓
GUI (main_window.py)
├─ Display video + timeline
├─ Allow manual editing
├─ Save/load project
    ↓
video_processor.py
├─ Cut clips (stream copy or re-encode)
├─ Merge clips (concat demuxer)
└─ Output: MP4 files
```

---

## ⚙️ Configuration

**Default settings** in `config.py`:
- `frame_sample_interval`: 2.0s (sample rate)
- `audio_spike_threshold`: 0.8 (0-1)
- `template_match_threshold`: 0.75 (0-1)
- `scene_change_threshold`: 30.0
- `highlight_pad_before`: 3.0s
- `highlight_pad_after`: 2.0s
- `death_detect_enabled`: true
- `ffmpeg_path`: "ffmpeg"
- `player_name`: "" (for OCR)

**User settings** saved to `settings.json` (only differences from defaults).

---

## 🔌 Dependencies

### Required
- **opencv-python** - Image processing, template matching
- **numpy** - Numerical operations, audio processing
- **scipy** - Signal processing
- **PyQt6** - GUI framework
- **torch** - GPU detection

### Optional
- **easyocr** - OCR for kill feed text recognition

### External
- **ffmpeg** - Video encoding/decoding (must be installed separately)

---

## 🚀 Quick Start

### Development

```bash
# Setup
pip install -r requirements.txt

# Run app
python main.py

# Verify
python -m py_compile core/*.py gui/*.py
```

### Usage

```bash
python main.py
  → File → Open (select video)
  → Detect → Auto Detect (matches + highlights)
  → Export → Select output folder
```

---

## 📊 Performance (v2.0 Optimizations)

| Component | Optimization | Speedup |
|-----------|--------------|---------|
| Audio | NumPy vectorized | 10x |
| Scene | Early resize | 2.6x |
| Match | Frame downscale | 1.2x |
| Parallel | ThreadPoolExecutor | 2-3x |
| **Total** | Combined | **4x** |

---

## ✨ Key Features

✓ Template matching for game boundaries
✓ Multi-signal highlight detection (audio + scene + OCR)
✓ Manual editing (drag timeline, add/delete highlights)
✓ Flexible export (individual clips or merged)
✓ Project save/load (JSON format)
✓ Parallel processing (4x faster in v2.0)
✓ Configurable quality/speed trade-off

---

## 🔗 Related

- FFmpeg docs: https://ffmpeg.org/documentation.html
- OpenCV docs: https://docs.opencv.org/
- NumPy docs: https://numpy.org/doc/
- PyQt6 docs: https://www.riverbankcomputing.com/static/Docs/PyQt6/

---

**Last Updated:** 2026-08-09
**Version:** 2.0 (Optimized)
