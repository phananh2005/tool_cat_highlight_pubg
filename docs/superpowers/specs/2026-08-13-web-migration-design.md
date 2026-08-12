# Web Migration Design - PUBG Highlight Cutter

## Purpose
Chuyển giao diện desktop PyQt6 sang Web UI (FastAPI + React) để nâng cấp trải nghiệm UX/UI.

## Architecture
- **Backend (FastAPI)**:
  - Tái sử dụng logic lõi (`core/`).
  - REST API: `/api/detect/matches`, `/api/detect/highlights`, `/api/export`.
  - Static Server: Serve video file local để Frontend xem.
- **Frontend (React/Vite)**:
  - Dark mode, micro-animations.
  - Video Player (HTML5 `<video>`).
  - Timeline Component: Cho phép kéo thả chỉnh sửa start/end highlight.

## Data Flow
1. User chọn video (đường dẫn local) qua UI.
2. Frontend gọi `/api/detect...` -> Backend xử lý, trả về JSON.
3. Frontend render video và timeline dựa trên JSON.
4. User sửa timeline, bấm export -> Gửi cấu hình về `/api/export`.

## Isolation
- API layer tách rời logic xử lý video.
- Frontend không cần biết cách nhận diện, chỉ làm việc với JSON & Video Stream.
