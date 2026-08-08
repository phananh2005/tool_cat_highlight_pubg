"""Detect highlight moments trong video PUBG.

Kết hợp nhiều tín hiệu:
1. Audio spike: đỉnh âm lượng (tiếng súng, reaction)
2. Scene change: frame difference đột biến
3. Kill feed OCR: tên tuyển thủ xuất hiện trong kill feed

Score fusion → vượt threshold = highlight.
"""
from __future__ import annotations

import subprocess
import tempfile
import struct
from pathlib import Path
from typing import Callable, Optional

import cv2
import numpy as np

from core.models import Highlight, Match


# ---------------------------------------------------------------------------
# Audio spike detection
# ---------------------------------------------------------------------------

def _extract_audio_raw(video_path: str, ffmpeg: str = "ffmpeg") -> tuple[np.ndarray, int]:
    """Trích xuất audio từ video bằng FFmpeg → raw PCM 16-bit mono.

    Returns (samples_array, sample_rate).
    """
    sample_rate = 16000
    cmd = [
        ffmpeg, "-i", video_path,
        "-vn", "-ac", "1", "-ar", str(sample_rate),
        "-f", "s16le", "-acodec", "pcm_s16le",
        "pipe:1",
    ]
    proc = subprocess.run(cmd, capture_output=True, timeout=600)
    if proc.returncode != 0:
        return np.array([], dtype=np.float32), sample_rate

    raw = proc.stdout
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    return samples, sample_rate


def _detect_audio_spikes(
    samples: np.ndarray,
    sample_rate: int,
    window_sec: float = 0.5,
    threshold: float = 0.8,
) -> list[tuple[float, float]]:
    """Tìm vùng có audio RMS cao bất thường.

    Returns list of (start_sec, peak_rms).
    """
    if len(samples) == 0:
        return []

    window_size = int(sample_rate * window_sec)
    hop = window_size // 2
    rms_values: list[tuple[float, float]] = []

    for i in range(0, len(samples) - window_size, hop):
        chunk = samples[i:i + window_size]
        rms = float(np.sqrt(np.mean(chunk ** 2)))
        time_sec = i / sample_rate
        rms_values.append((time_sec, rms))

    if not rms_values:
        return []

    # Normalize RMS to 0-1
    max_rms = max(r for _, r in rms_values)
    if max_rms < 1e-6:
        return []

    spikes = [(t, r / max_rms) for t, r in rms_values if r / max_rms >= threshold]
    return spikes


# ---------------------------------------------------------------------------
# Scene change detection
# ---------------------------------------------------------------------------

def _detect_scene_changes(
    video_path: str,
    sample_interval: float = 1.0,
    threshold: float = 30.0,
    progress_cb: Optional[Callable[[float, str], None]] = None,
) -> list[tuple[float, float]]:
    """Tìm thời điểm frame difference đột biến.

    Returns list of (time_sec, diff_score).
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_step = max(1, int(fps * sample_interval))

    prev_gray = None
    changes: list[tuple[float, float]] = []
    frame_idx = 0

    while frame_idx < total_frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ok, frame = cap.read()
        if not ok:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, (320, 180))  # downscale for speed

        if prev_gray is not None:
            diff = float(np.mean(np.abs(gray.astype(float) - prev_gray.astype(float))))
            if diff >= threshold:
                t = frame_idx / fps
                changes.append((t, diff))

        prev_gray = gray
        frame_idx += frame_step

    cap.release()
    return changes


# ---------------------------------------------------------------------------
# Kill feed OCR (optional — heavy dependency)
# ---------------------------------------------------------------------------

_ocr_reader = None

def _get_ocr_reader():
    global _ocr_reader
    if _ocr_reader is None:
        try:
            import easyocr
            _ocr_reader = easyocr.Reader(["en"], gpu=False)
        except ImportError:
            return None
    return _ocr_reader


def _detect_kill_feed(
    video_path: str,
    player_name: str,
    kill_feed_region: list[float],
    sample_interval: float = 2.0,
) -> list[tuple[float, float]]:
    """OCR vùng kill feed, tìm tên tuyển thủ.

    kill_feed_region: [x1_ratio, y1_ratio, x2_ratio, y2_ratio] (0-1).
    Returns list of (time_sec, confidence).
    """
    if not player_name:
        return []

    reader = _get_ocr_reader()
    if reader is None:
        return []

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_step = max(1, int(fps * sample_interval))

    kills: list[tuple[float, float]] = []
    x1r, y1r, x2r, y2r = kill_feed_region
    player_lower = player_name.lower()

    frame_idx = 0
    while frame_idx < total_frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ok, frame = cap.read()
        if not ok:
            break

        h, w = frame.shape[:2]
        x1, y1 = int(w * x1r), int(h * y1r)
        x2, y2 = int(w * x2r), int(h * y2r)
        crop = frame[y1:y2, x1:x2]

        try:
            results = reader.readtext(crop, detail=1)
            for bbox, text, conf in results:
                if player_lower in text.lower():
                    t = frame_idx / fps
                    kills.append((t, conf))
                    break
        except Exception:
            pass

        frame_idx += frame_step

    cap.release()
    return kills


# ---------------------------------------------------------------------------
# Score fusion
# ---------------------------------------------------------------------------

def detect_highlights(
    video_path: str,
    matches: list[Match],
    player_name: str = "",
    config: Optional[dict] = None,
    progress_cb: Optional[Callable[[float, str], None]] = None,
) -> list[Highlight]:
    """Phát hiện tất cả highlight trong video.

    Kết hợp audio spikes + scene changes + kill feed OCR.
    Gán mỗi highlight vào match tương ứng.

    Args:
        video_path: đường dẫn video
        matches: danh sách Match đã detect
        player_name: tên in-game (cho OCR)
        config: dict config
        progress_cb: callback(progress_0_to_1, status_text)
    """
    from config import DEFAULTS
    cfg = {**DEFAULTS, **(config or {})}

    pad_before = cfg["highlight_pad_before"]
    pad_after = cfg["highlight_pad_after"]
    min_gap = cfg["highlight_min_gap"]

    # --- Step 1: Audio spikes ---
    if progress_cb:
        progress_cb(0.0, "Đang phân tích audio...")

    samples, sr = _extract_audio_raw(video_path, cfg["ffmpeg_path"])
    audio_spikes = _detect_audio_spikes(
        samples, sr, threshold=cfg["audio_spike_threshold"]
    )

    if progress_cb:
        progress_cb(0.33, "Đang phân tích scene changes...")

    # --- Step 2: Scene changes ---
    scene_changes = _detect_scene_changes(
        video_path,
        sample_interval=cfg["frame_sample_interval"],
        threshold=cfg["scene_change_threshold"],
    )

    if progress_cb:
        progress_cb(0.66, "Đang đọc kill feed (OCR)...")

    # --- Step 3: Kill feed OCR ---
    kills = _detect_kill_feed(
        video_path, player_name,
        cfg["kill_feed_region"],
        sample_interval=cfg["frame_sample_interval"],
    )

    # --- Step 4: Merge all signals into time-score map ---
    # Tạo timeline bins (mỗi bin = 1 second)
    cap = cv2.VideoCapture(video_path)
    total_duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / max(cap.get(cv2.CAP_PROP_FPS), 1)
    cap.release()

    num_bins = int(total_duration) + 1
    scores = np.zeros(num_bins, dtype=np.float32)
    types = [""] * num_bins

    # Audio spikes: weight 0.4
    for t, s in audio_spikes:
        idx = int(t)
        if 0 <= idx < num_bins:
            scores[idx] += s * 0.4
            types[idx] = "audio_spike"

    # Scene changes: weight 0.3 (normalize)
    if scene_changes:
        max_sc = max(s for _, s in scene_changes)
        for t, s in scene_changes:
            idx = int(t)
            if 0 <= idx < num_bins:
                scores[idx] += (s / max_sc) * 0.3
                if not types[idx]:
                    types[idx] = "scene_change"

    # Kill feed: weight 0.5 (highest signal)
    for t, s in kills:
        idx = int(t)
        if 0 <= idx < num_bins:
            scores[idx] += s * 0.5
            types[idx] = "kill"  # overrides other types

    # --- Step 5: Threshold + merge nearby ---
    combined_threshold = 0.3  # ponytail: low threshold, user filters later
    raw_highlights: list[tuple[float, float, float, str]] = []

    for i in range(num_bins):
        if scores[i] >= combined_threshold:
            raw_highlights.append((float(i), scores[i], scores[i], types[i] or "mixed"))

    # Merge highlights gần nhau
    merged = _merge_nearby(raw_highlights, min_gap, pad_before, pad_after, total_duration)

    # --- Step 6: Gán match index ---
    highlights: list[Highlight] = []
    for start, end, conf, htype in merged:
        mi = _find_match_index(start, matches)
        highlights.append(Highlight(
            start_time=start,
            end_time=end,
            confidence=min(conf, 1.0),
            highlight_type=htype,
            match_index=mi,
        ))

    if progress_cb:
        progress_cb(1.0, "Hoàn tất detect highlights.")

    return highlights


def _merge_nearby(
    raw: list[tuple[float, float, float, str]],
    min_gap: float,
    pad_before: float,
    pad_after: float,
    total_duration: float,
) -> list[tuple[float, float, float, str]]:
    """Gộp highlights gần nhau và áp dụng padding."""
    if not raw:
        return []

    merged: list[tuple[float, float, float, str]] = []
    cur_start = max(0, raw[0][0] - pad_before)
    cur_end = min(total_duration, raw[0][0] + pad_after)
    cur_conf = raw[0][1]
    cur_type = raw[0][3]

    for t, score, conf, htype in raw[1:]:
        new_start = max(0, t - pad_before)
        new_end = min(total_duration, t + pad_after)

        if new_start - cur_end <= min_gap:
            # Merge
            cur_end = max(cur_end, new_end)
            cur_conf = max(cur_conf, conf)
            if htype == "kill":
                cur_type = "kill"
        else:
            merged.append((cur_start, cur_end, cur_conf, cur_type))
            cur_start = new_start
            cur_end = new_end
            cur_conf = conf
            cur_type = htype

    merged.append((cur_start, cur_end, cur_conf, cur_type))
    return merged


def _find_match_index(time_sec: float, matches: list[Match]) -> int:
    """Tìm highlight thuộc match nào."""
    for m in matches:
        if m.start_time <= time_sec <= m.end_time:
            return m.index
    # Fallback: match gần nhất
    if matches:
        return min(matches, key=lambda m: abs(m.start_time - time_sec)).index
    return 0
