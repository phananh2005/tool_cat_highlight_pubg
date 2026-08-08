"""Detect ranh giới game (match) trong file livestream PUBG.

Dùng OpenCV template matching để nhận diện lobby, loading, winner/death screen.
Sample frame mỗi N giây (configurable), không cần duyệt mọi frame.
"""
from __future__ import annotations

import cv2
import numpy as np
from pathlib import Path
from typing import Callable, Optional

from core.models import Match


def _load_templates(templates_dir: str | Path) -> dict[str, np.ndarray]:
    """Load tất cả template images từ thư mục templates/."""
    templates = {}
    tdir = Path(templates_dir)
    if not tdir.exists():
        return templates
    for f in tdir.iterdir():
        if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".bmp"):
            img = cv2.imread(str(f), cv2.IMREAD_COLOR)
            if img is not None:
                templates[f.stem] = img
    return templates


def _match_template(frame: np.ndarray, template: np.ndarray, threshold: float) -> float:
    """So khớp template với frame. Trả về max score."""
    # Resize template nếu lớn hơn frame
    fh, fw = frame.shape[:2]
    th, tw = template.shape[:2]
    if th > fh or tw > fw:
        scale = min(fh / th, fw / tw) * 0.9
        template = cv2.resize(template, (int(tw * scale), int(th * scale)))

    result = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
    return float(result.max())


def detect_matches(
    video_path: str,
    templates_dir: str | Path,
    sample_interval: float = 2.0,
    threshold: float = 0.75,
    min_match_duration: float = 60.0,
    progress_cb: Optional[Callable[[float], None]] = None,
) -> list[Match]:
    """Phát hiện ranh giới game trong video.

    Args:
        video_path: đường dẫn file video
        templates_dir: thư mục chứa template images (lobby.png, loading.png, winner.png...)
        sample_interval: giây giữa mỗi lần sample frame
        threshold: ngưỡng template matching (0-1)
        min_match_duration: game ngắn hơn X giây thì bỏ qua (lọc false positive)
        progress_cb: callback(progress_0_to_1) để cập nhật tiến trình

    Returns:
        Danh sách Match đã sắp xếp theo thời gian
    """
    templates = _load_templates(templates_dir)
    if not templates:
        # Không có template → coi toàn bộ video là 1 game
        cap = cv2.VideoCapture(video_path)
        total = cap.get(cv2.CAP_PROP_FRAME_COUNT) / max(cap.get(cv2.CAP_PROP_FPS), 1)
        cap.release()
        return [Match(index=0, start_time=0.0, end_time=total)]

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Không mở được video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    total_duration = total_frames / fps
    frame_step = int(fps * sample_interval)

    # Duyệt frame, ghi nhận thời điểm match template
    transition_times: list[float] = []
    frame_idx = 0

    while True:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ok, frame = cap.read()
        if not ok:
            break

        current_time = frame_idx / fps

        # Kiểm tra từng template
        for name, tmpl in templates.items():
            score = _match_template(frame, tmpl, threshold)
            if score >= threshold:
                transition_times.append(current_time)
                break  # 1 match là đủ cho frame này

        if progress_cb:
            progress_cb(min(frame_idx / total_frames, 1.0))

        frame_idx += frame_step
        if frame_idx >= total_frames:
            break

    cap.release()

    # Gộp transition points thành match boundaries
    matches = _build_matches_from_transitions(transition_times, total_duration, min_match_duration)

    if progress_cb:
        progress_cb(1.0)

    return matches


def _build_matches_from_transitions(
    transitions: list[float],
    total_duration: float,
    min_duration: float,
) -> list[Match]:
    """Từ danh sách thời điểm transition, xây dựng match list.

    Logic: các transition gần nhau (< 30s) thuộc cùng 1 vùng "giữa game".
    Khoảng trống lớn giữa 2 cụm transition = 1 game.
    """
    if not transitions:
        return [Match(index=0, start_time=0.0, end_time=total_duration)]

    # Gộp transitions gần nhau thành clusters
    clusters: list[tuple[float, float]] = []  # (start, end) của mỗi cluster
    cluster_start = transitions[0]
    cluster_end = transitions[0]

    for t in transitions[1:]:
        if t - cluster_end < 30.0:  # < 30s gap → cùng cluster
            cluster_end = t
        else:
            clusters.append((cluster_start, cluster_end))
            cluster_start = t
            cluster_end = t
    clusters.append((cluster_start, cluster_end))

    # Mỗi khoảng giữa 2 clusters = 1 game
    matches: list[Match] = []
    idx = 0

    # Game đầu tiên: từ 0 đến cluster đầu
    if clusters[0][0] > min_duration:
        matches.append(Match(index=idx, start_time=0.0, end_time=clusters[0][0]))
        idx += 1

    # Games giữa
    for i in range(len(clusters) - 1):
        gap_start = clusters[i][1]
        gap_end = clusters[i + 1][0]
        if gap_end - gap_start >= min_duration:
            matches.append(Match(index=idx, start_time=gap_start, end_time=gap_end))
            idx += 1

    # Game cuối: từ cluster cuối đến hết video
    if total_duration - clusters[-1][1] > min_duration:
        matches.append(Match(index=idx, start_time=clusters[-1][1], end_time=total_duration))
        idx += 1

    # Fallback: nếu không detect được game nào → coi toàn bộ là 1 game
    if not matches:
        matches = [Match(index=0, start_time=0.0, end_time=total_duration)]

    return matches
