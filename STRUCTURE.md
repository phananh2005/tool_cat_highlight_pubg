# Project Structure

Dự án sử dụng mô hình Client - Server tách biệt hoàn toàn để tối ưu hiệu năng.

```
tool_cat_highlight_yt/
│
├── ⚙️ Backend (Python / FastAPI)
│   ├── main_api.py              # Entry point của Server (API Routes)
│   ├── config.py                # Quản lý cấu hình Settings
│   ├── requirements.txt         # Thư viện Python
│   ├── settings.json            # File cấu hình (tự sinh)
│   │
│   ├── core/                    # Xử lý Logic cốt lõi
│   │   ├── models.py            # Cấu trúc dữ liệu (Match, Highlight, Project)
│   │   ├── match_detector.py    # Nhận diện đầu/cuối game (Computer Vision)
│   │   ├── highlight_detector.py# Nhận diện tiếng súng, chuyển cảnh (Audio/CV)
│   │   └── video_processor.py   # Điều khiển FFmpeg để cắt ghép MP4
│   │
│   ├── templates/               # Ảnh mẫu để Template Matching (Lobby, Winner...)
│   │
│   └── exports/                 # Thư mục chứa các clip MP4 đã xuất thành công
│
├── 🎨 Frontend (React / Vite)
│   └── web/
│       ├── index.html           
│       ├── package.json         # Thư viện Node.js
│       ├── tailwind.config.js   # Cấu hình UI CSS
│       └── src/                 # Source code giao diện Web
│           ├── App.jsx          # Component chính (Quản lý State, Shortcuts, Lưu/Mở)
│           ├── Timeline.jsx     # Component vẽ giao diện Editor cắt clip
│           ├── ExportProgressModal.jsx # Component hiển thị thanh Progress Bar
│           ├── SettingsModal.jsx# Giao diện cấu hình
│           └── App.css          # CSS toàn cục
│
└── 🔧 Tài liệu
    ├── README.md                # Hướng dẫn chung
    └── STRUCTURE.md             # Sơ đồ cấu trúc (file này)
```

## Luồng dữ liệu (Data Flow)
1. **Detect**: `App.jsx` gọi POST `/api/detect/highlights`. Backend dùng `core/highlight_detector.py` quét video bằng PyTorch/OpenCV và trả về mảng JSON.
2. **Edit**: Người dùng thao tác kéo thả trên Web UI, React cập nhật State cục bộ.
3. **Save**: Người dùng xuất file `.json` chứa state về máy tính.
4. **Export**: 
   - `App.jsx` gửi POST `/api/export`. 
   - Backend đẩy lệnh vào `BackgroundTasks` và lập tức trả về `status = started`.
   - `App.jsx` liên tục gọi GET `/api/export/status` mỗi 500ms.
   - Backend dùng `video_processor.py` báo cáo % thông qua biến global `_export_state`.
   - Thanh tiến trình trên Web chạy mượt mà đến 100%.
