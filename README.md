# PUBG Highlight Cutter (Web Edition)

Công cụ tự động phát hiện và cắt highlight từ livestream PUBG. Chạy hoàn toàn trên trình duyệt với sức mạnh xử lý đa luồng (Background Tasks) ở Backend.

## 🎯 Tính năng nổi bật

- **⚡ Phát hiện Highlight tự động**: Quét file video để tìm các khoảnh khắc bắn súng (Audio spike), chuyển cảnh (Scene change) và chữ Kill trên màn hình (OCR).
- **🌐 Giao diện Web (Pro Editor)**:
  - Timeline Editor kéo thả mượt mà, zoom chi tiết đến từng mili-giây.
  - Hỗ trợ Phím tắt (Space để Play/Pause, Mũi tên để tua 5s).
  - Quản lý phiên làm việc: **Lưu Project** (tải file .json) và **Mở Project** (khôi phục dữ liệu).
- **🚀 Xử lý nền (Background Tasks)**:
  - Quá trình cắt ghép video được thực thi ngầm trên Server (FastAPI).
  - Frontend hiển thị thanh Tiến độ (Progress Bar) % theo thời gian thực (Polling). Không lo đơ trình duyệt.
- **⚡ GPU Acceleration**: Hỗ trợ NVIDIA CUDA (PyTorch) giúp việc detect nhanh hơn 40%.

---

## 🚀 Hướng dẫn Cài đặt & Chạy

Kiến trúc phần mềm chia làm 2 phần: **Backend (Python)** và **Frontend (React)**. Cần chạy song song cả hai.

### 1. Khởi động Backend (FastAPI)

Yêu cầu: Python 3.8+ và đã cài đặt FFmpeg trên máy.

```bash
# Cài đặt thư viện Python
pip install -r requirements.txt

# Chạy server API (Cổng 8000)
python main_api.py
```

### 2. Khởi động Frontend (React/Vite)

Mở một cửa sổ Terminal khác:

```bash
# Chuyển vào thư mục web
cd web

# Cài đặt thư viện Node
npm install

# Khởi động giao diện Web (Cổng 5173)
npm run dev
```

Sau khi chạy xong, mở trình duyệt truy cập: **http://localhost:5173**

---

## 📖 Hướng dẫn Sử dụng

1. **Load Video**: Nhập đường dẫn gốc của video trên máy tính (VD: `C:\videos\stream.mp4`).
2. **Detect Matches**: Bấm để tìm các ranh giới của từng game trong luồng stream dài.
3. **Detect Highlights**: Bấm để quét âm thanh tiếng súng và hình ảnh để bắt Highlight. (Có thể mất vài phút).
4. **Edit Timeline**:
   - Bấm nút "+ Thêm Clip Tại Đây" hoặc kéo thanh giới hạn để chỉnh sửa Highlight.
   - Sử dụng nút có hình "Mắt" để Bật/Tắt các clip rác.
5. **Lưu/Mở Project**: Bấm nút **💾 Lưu Project** để cất dữ liệu nếu chưa làm xong. Hôm sau bấm **📂 Mở Project** để làm tiếp.
6. **Export Clips**: Bấm nút Export màu vàng. Một cửa sổ sẽ hiện ra tiến trình cắt video % đến khi hoàn tất. Video thành phẩm nằm ở thư mục `exports/`.

---

## ⚙️ Thiết lập Nâng cao (Settings)

Bấm vào nút **⚙️ Settings** trên Web để điều chỉnh:

- **Audio Spike Threshold**: Ngưỡng âm lượng để xác định tiếng súng. Càng nhỏ thì càng dễ bắt (nhưng dễ nhiễu).
- **Padding**: Số giây lấy dư ra ở đằng trước và đằng sau lúc bắn để clip không bị cụt.
- **FFmpeg Path**: Nếu máy tính chưa nhận biến môi trường FFmpeg, bạn có thể trỏ thẳng đường dẫn `ffmpeg.exe` vào đây.
