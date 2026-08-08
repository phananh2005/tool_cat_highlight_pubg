# Hướng dẫn nhanh - PUBG Highlight Cutter

## Cài đặt nhanh

```bash
pip install -r requirements.txt
python main.py
```

**Lưu ý:** Cần cài FFmpeg trước (https://ffmpeg.org/download.html)

## Quy trình sử dụng

### 1. Mở file livestream
- File → Open (hoặc drag-drop file MP4/MKV)

### 2. Phát hiện game boundaries
- Detect → Match Boundaries
- Cần ảnh template trong thư mục `templates/` (lobby.png, loading.png, winner.png)

### 3. Phát hiện highlights
- Detect → Highlights
- Nếu muốn OCR kill feed: nhập tên tuyển thủ trong Settings trước

### 4. Chỉnh sửa thủ công
- Click timeline để seek
- Kéo handles để chỉnh thời gian
- Right-click để thêm/xóa/sửa

### 5. Export
- Export → Selected (hoặc All)
- Chọn output folder
- Chọn riêng lẻ hay gộp theo game

## Cài đặt quan trọng

**Settings → Player Name:** Nhập tên in-game để OCR phát hiện kill feed

**Settings → Kill Feed Region:** Vùng crop kill feed (mặc định: 0.65, 0.0, 1.0, 0.35)

## Template matching

Cứ 1 game PUBG có những màn hình chuẩn:
1. Lobby (trước vào game)
2. Loading (đang load)
3. Winner/Death (kết thúc game)

Cắt screenshot của 3 màn hình này từ livestream thật, resize 320x180, save vào `templates/`:
- `lobby.png`
- `loading.png`
- `winner.png`

Tool sẽ tự động load khi phát hiện.

## Lưu project

**File → Save Project:** Lưu matches + highlights vào .json
**File → Load Project:** Nạp lại sau này mà không cần re-detect

## Troubleshooting

| Vấn đề | Giải pháp |
|--------|----------|
| FFmpeg not found | Cài FFmpeg, cập nhật đường dẫn trong Settings |
| Detect không chính xác | Cung cấp ảnh template thực tế |
| OCR fail | Cài easyocr: `pip install easyocr`, hoặc tắt (xóa player_name) |
| Audio spike quá nhạy | Tăng `audio_spike_threshold` trong Settings |

## Files quan trọng

- `main.py` - Entry point
- `config.py` - Settings & defaults
- `core/` - Detection engines
- `gui/` - GUI components
- `templates/` - Ảnh mẫu game UI
- `settings.json` - User config (auto-generated)
