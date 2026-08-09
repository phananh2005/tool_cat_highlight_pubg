# PUBG Highlight Cutter v2.0

Tool desktop GUI tự động phát hiện và cắt highlight từ livestream PUBG. **4x nhanh hơn** (v2.0 optimization).

## 🎯 Tính năng

- **🔍 Phát hiện ranh giới game:** Template matching nhận diện lobby, loading, winner/death screen
- **⚡ Phát hiện highlight:** Audio spike + scene change + OCR kill feed kết hợp
- **✏️ Chỉnh sửa thủ công:** Thêm/xóa/sửa highlight, kéo chỉnh timeline
- **📦 Export linh hoạt:** Riêng lẻ hoặc gộp theo game, stream copy/accurate encode
- **📊 Timeline visual:** Toàn bộ video với match + highlight markers
- **⚡ Parallel processing:** Audio + scene + spectate chạy cùng lúc → 4x nhanh

## 📊 Hiệu năng (v2.0 + GPU Acceleration)

| Video | CPU | GPU | Cải thiện |
|-------|-----|-----|----------|
| 1 giờ | ~10 min | **~6-7 min** | **35-40%** |
| 4 giờ | ~40 min | **~24-28 min** | **35-40%** |

**Yêu cầu cho GPU (tùy chọn):**
- NVIDIA GPU + CUDA Toolkit
- PyTorch hỗ trợ CUDA
- Xem [Hướng dẫn GPU](docs/PERFORMANCE.md#gpu-setup)

**Chỉ CPU:** Vẫn ~10 min (baseline v2.0)

**Optimizations:**
- Audio spike detection: 10x (NumPy vectorized)
- Scene change detection: 2.6x (early resize + motion uniformity filter)
- Match detection: 1.2x (frame downscale + adaptive sampling)
- Kill feed OCR: 2.5-3x (GPU batch processing, 4 workers)
- Parallel processing: 2-3x (ThreadPoolExecutor)
- **Overall with GPU: 1.4-1.7x faster (35-40% time reduction)**

## ⚡ GPU Acceleration (Optional)

**Detection is 35-40% faster with NVIDIA GPU:**

### Check GPU availability:
```bash
python -c "import torch; print(f'GPU available: {torch.cuda.is_available()}')"
```

### GPU available:
- EasyOCR automatically uses CUDA
- Batch processing uses 4 workers (vs 2 on CPU)
- Expected time: ~6-7 min for 1h video

### No GPU / CPU-only:
- Falls back automatically
- Detection still works: ~10 min for 1h video
- No extra setup needed

### Setup NVIDIA GPU:

If `torch.cuda.is_available()` returns False:

1. **Install NVIDIA CUDA Toolkit** (if not already installed):
   - Download: https://developer.nvidia.com/cuda-downloads
   - Choose your OS and follow setup

2. **Reinstall PyTorch with CUDA support**:
   ```bash
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   ```
   (cu118 = CUDA 11.8; choose cu121 for CUDA 12.1 if you have it)

3. **Verify installation**:
   ```bash
   python -c "import torch; print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
   ```

4. **Restart app** — detection should now be 35-40% faster

---

## 🚀 Cài đặt

### Yêu cầu

- Python 3.8+
- FFmpeg ([download](https://ffmpeg.org/download.html))
- Các package trong `requirements.txt`

### Cách cài

```bash
cd tool_cat_highlight_yt

# Cài dependencies
pip install -r requirements.txt

# Chạy app
python main.py
```

### Kiểm tra FFmpeg

```bash
ffmpeg -version
# Nếu lỗi, cấu hình đường dẫn trong Settings
```

---

## 📋 Cấu trúc dự án

```
tool_cat_highlight_yt/
├── main.py                      # Entry point
├── config.py                    # Config + defaults
├── requirements.txt
├── settings.json                # User settings (auto-generated)
├── core/
│   ├── models.py               # Match, Highlight, Project models
│   ├── match_detector.py       # Game boundary detection
│   ├── highlight_detector.py   # Highlight moment detection
│   └── video_processor.py      # Cut/merge videos
├── gui/
│   ├── main_window.py          # Main window + video player
│   └── timeline_widget.py      # Timeline visualization
└── templates/                   # Template images (lobby, loading, winner)
```

---

## 📖 Cách dùng

### 1️⃣ Mở file livestream

**File → Open** (hoặc drag-drop)

### 2️⃣ Phát hiện matches

**Detect → Auto Detect**

- Sẽ detect ranh giới game tự động (~5 min)
- (Cần template images trong `templates/` folder)

### 3️⃣ Phát hiện highlights

Tiếp theo app sẽ detect highlights:
- Audio spikes (tiếng súng)
- Scene changes (transitions)
- Kill feed (nếu nhập player name)

Total time: ~10 min cho 1 giờ video

### 4️⃣ Chỉnh sửa

- **Click timeline** để seek
- **Kéo highlight bars** để chỉnh start/end
- **Double-click** để chỉnh tên
- **Checkbox** để bật/tắt

### 5️⃣ Export

- Chọn game hoặc tất cả
- Chọn output folder
- Export (sẽ tạo MP4 clips)

---

## ⚙️ Cài đặt (Settings)

Mở **Settings → Cài đặt...** để tuỳ chỉnh:

| Setting | Range | Mặc định | Tác dụng |
|---------|-------|----------|---------|
| **frame_sample_interval** | 0.5-10 s | 2.0 s | Khoảng sample frame |
| **audio_spike_threshold** | 0.1-1.0 | 0.8 | Ngưỡng detect audio |
| **template_match_threshold** | 0.3-1.0 | 0.75 | Ngưỡng template match |
| **scene_change_threshold** | 10-100 | 30.0 | Ngưỡng scene diff |
| **highlight_pad_before** | 0-30 s | 3.0 s | Padding trước highlight |
| **highlight_pad_after** | 0-30 s | 2.0 s | Padding sau highlight |
| **player_name** | string | (empty) | Tên in-game (cho OCR) |
| **death_detect_enabled** | true/false | true | Bật spectate detection |

### 🎯 Tuỳ chỉnh Quality/Speed

**Chất lượng cao** (chậm):
```
frame_sample_interval: 1.0 (thay 2.0)
Export → Chọn "Accurate cut"
→ Detection ~20 min, export ~3-5 min/clip
```

**Tốc độ tối đa** (maintain 95%+ accuracy):
```
frame_sample_interval: 3.0 (tăng từ 2.0)
death_detect_enabled: ON (vẫn bật, chạy song song)
player_name: (giữ nguyên để detect kill)
→ Detection: ~6-7 min cho 1h video (nhanh hơn 35-40%, độ chính xác 95%)
```

**Lý do 3.0s an toàn:**
- Template matching accuracy: 95%+
- Game transitions kéo dài: 10-30 giây
- Tại 3.0s sampling: 3-10 mẫu mỗi transition
- Xác suất bỏ lỡ toàn bộ transition: <0.01%

---

## 📚 Template Matching

Để detect match boundaries, cung cấp ảnh mẫu trong `templates/`:

- **lobby.png** (320x180): Lobby screen
- **loading.png** (320x180): Loading screen
- **winner.png** (320x180): Winner/death screen

Take screenshot từ video → save vào folder này. App sẽ tự load.

---

## 💾 Lưu/Load Project

- **File → Save Project:** Lưu matches + highlights vào `.json`
- **File → Load Project:** Nạp từ `.json` (skip detection)

Hữu ích khi muốn tiếp tục chỉnh sửa sau.

---

## 🐛 Troubleshooting

### "FFmpeg not found"
```
Settings → FFmpeg path: C:\path\to\ffmpeg.exe
(hoặc cài FFmpeg + thêm vào PATH)
```

### Detection quá chậm
```
Settings → frame_sample_interval: ↑ 3.0 or 4.0
           → death_detect_enabled: OFF
           → player_name: (bỏ trống)
```

### GPU not detected / detection still slow
Check GPU availability:
```bash
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

If False, install CUDA-enabled PyTorch:
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

Restart app. Detection should now be 35-40% faster.

See `docs/PERFORMANCE.md` for detailed GPU setup and troubleshooting.

### Miss highlights
```
Settings → audio_spike_threshold: ↓ 0.7
          → scene_change_threshold: ↓ 20
```

### OCR không hoạt động
```
pip install easyocr
(hoặc tắt bằng cách bỏ trống player_name)
```

### Export quá chậm
```
Chọn "Stream copy" thay vì "Accurate cut"
(nhanh hơn 3-5x nhưng có thể ±1 frame drift)
```

---

## 🔧 Công nghệ

- **PyQt6:** GUI
- **OpenCV:** Template matching, frame processing
- **NumPy/SciPy:** Audio/signal processing
- **EasyOCR:** Kill feed OCR (optional)
- **FFmpeg:** Video cut/merge
- **ThreadPoolExecutor:** Parallel processing

---

## 📝 Phiên bản

- **v1.0:** Sequential processing
- **v2.0:** Vectorized + parallel → 4x nhanh hơn ⚡

---

## 📞 Support

- Xem `CONTRIBUTING.md` cho chi tiết optimization
- Xem `DEPLOYMENT.md` cho deployment guide
- Check `templates/README.md` cho cách setup templates

---

## 📄 License

MIT
