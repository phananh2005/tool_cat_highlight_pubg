# Web UI Perfection Design

## Purpose
Nâng cấp toàn diện giao diện Web cho PUBG Highlight Cutter, đạt chuẩn Premium UI và đẩy đủ tính năng như bản Desktop (Timeline tương tác, Export, Settings).

## Giai đoạn 1: Premium UI & Export (Chức năng cốt lõi)
- **UI Framework**: Tích hợp Tailwind CSS để style nhanh và chuẩn.
- **Layout mới**: 
  - Header: Tiêu đề + Nút Settings.
  - Main: Video Player lớn ở trung tâm.
  - Sidebar: Danh sách Matches và Highlights có scroll.
- **Chức năng Export**:
  - Gửi danh sách highlights đã chọn về backend.
  - Backend gọi `core.video_processor.export_clips`.
- **Settings Modal**:
  - Cho phép cấu hình `sample_interval`, `audio_spike_threshold`, v.v. trước khi detect.

## Giai đoạn 2: Interactive Timeline (Trải nghiệm Pro)
- **Timeline Component**:
  - Một thanh ngang bám dưới Video Player.
  - Trục thời gian (0 -> Tổng thời lượng video).
  - Vẽ các khối (blocks) đại diện cho Matches (màu xám) và Highlights (màu cam/đỏ).
- **Tương tác**:
  - Click vào timeline để seek video.
  - Kéo thả mép trái/phải của highlight block để thay đổi `start_time` và `end_time`.
  - Nút bật/tắt (enable/disable) từng highlight.
