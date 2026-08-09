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
import logging
from pathlib import Path
from typing import Callable, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import cv2
import numpy as np
import torch

from core.models import Highlight, Match

logger = logging.getLogger(__name__)


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
    logger.info(f"Extracting audio from {video_path}")
    proc = subprocess.run(cmd, capture_output=True, timeout=600)
    if proc.returncode != 0:
        logger.warning(f"FFmpeg audio extraction failed (exit code {proc.returncode})")
        return np.array([], dtype=np.float32), sample_rate

    raw = proc.stdout
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    logger.info(f"Audio extracted: {len(samples)} samples, sample_rate={sample_rate}")
    return samples, sample_rate


def _detect_audio_spikes(
    samples: np.ndarray,
    sample_rate: int,
    window_sec: float = 0.5,
    threshold: float = 0.8,
) -> list[tuple[float, float]]:
    """Tìm vùng có audio RMS cao bất thường (vectorized).

    Returns list of (start_sec, peak_rms).
    """
    if len(samples) == 0:
        logger.warning("No audio samples for spike detection")
        return []

    window_size = int(sample_rate * window_sec)
    hop = window_size // 2
    
    n_windows = (len(samples) - window_size) // hop + 1
    if n_windows <= 0:
        logger.warning("Not enough samples for window analysis")
        return []

    indices = np.arange(n_windows) * hop
    windowed = np.lib.stride_tricks.sliding_window_view(samples, window_size)[::hop][:n_windows]
    
    rms_arr = np.sqrt(np.mean(windowed ** 2, axis=1))
    
    max_rms = rms_arr.max()
    if max_rms < 1e-6:
        logger.info("Audio RMS too low (silent video)")
        return []
    
    normalized = rms_arr / max_rms
    mask = normalized >= threshold
    
    times = indices[:n_windows] / sample_rate
    spikes = [(float(t), float(r)) for t, r in zip(times[mask], normalized[mask])]
    
    logger.info(f"Audio spikes detected: {len(spikes)} spikes")
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
    logger.info(f"Detecting scene changes: video={video_path}, interval={sample_interval}s, threshold={threshold}")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error(f"Cannot open video for scene detection: {video_path}")
        return []

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_step = max(1, int(fps * sample_interval))
    target_size = (320, 180)

    logger.info(f"Video info: fps={fps:.2f}, total_frames={total_frames}, frame_step={frame_step}")

    prev_gray = None
    changes: list[tuple[float, float]] = []
    frame_idx = 0

    while frame_idx < total_frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ok, frame = cap.read()
        if not ok:
            break

        gray = cv2.resize(frame, target_size)
        gray = cv2.cvtColor(gray, cv2.COLOR_BGR2GRAY)

        if prev_gray is not None:
            diff = float(np.mean(np.abs(gray.astype(np.int16) - prev_gray.astype(np.int16))))
            if diff >= threshold:
                t = frame_idx / fps
                changes.append((t, diff))

        prev_gray = gray
        frame_idx += frame_step

    cap.release()
    logger.info(f"Scene changes detected: {len(changes)} events")
    return changes


# ---------------------------------------------------------------------------
# Death / Spectate detection
# ---------------------------------------------------------------------------

def _detect_spectate_intervals(
    video_path: str,
    spectate_region: list[float],
    brightness_max: float = 45.0,
    stddev_max: float = 20.0,
    sample_interval: float = 0.5,
    min_duration: float = 3.0,
    progress_cb: Optional[Callable[[float, str], None]] = None,
) -> list[tuple[float, float]]:
    """Detect khoảng thời gian player đang spectate (đã chết).

    Cải thiện: sample_interval 0.5s (thay 2s), brightness_max 45 (thay 60), stddev_max 20 (thay 35).
    Returns list of (start_sec, end_sec) spectate intervals.
    """
    logger.info(f"Detecting spectate intervals: video={video_path}, region={spectate_region}")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error(f"Cannot open video for spectate detection: {video_path}")
        return []

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_step = max(1, int(fps * sample_interval))

    logger.info(f"Video: fps={fps:.2f}, total_frames={total_frames}, frame_step={frame_step}")

    x1r, y1r, x2r, y2r = spectate_region
    is_spectate_list: list[tuple[float, bool]] = []  # (time, is_spectating)

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

        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        mean_b = np.mean(gray)
        std_b = np.std(gray)

        is_spec = mean_b < brightness_max and std_b < stddev_max
        t = frame_idx / fps
        is_spectate_list.append((t, is_spec))

        frame_idx += frame_step

    cap.release()

    if not is_spectate_list:
        logger.warning("No frames analyzed for spectate detection")
        return []

    intervals: list[tuple[float, float]] = []
    in_spectate = False
    start_time = 0.0
    spectate_count = 0

    for t, is_spec in is_spectate_list:
        if is_spec and not in_spectate:
            in_spectate = True
            start_time = t
            spectate_count = 1
        elif is_spec and in_spectate:
            spectate_count += 1
        elif not is_spec and in_spectate:
            in_spectate = False
            if t - start_time >= min_duration and spectate_count >= 3:
                intervals.append((start_time, t))

    if in_spectate:
        end_t = is_spectate_list[-1][0]
        if end_t - start_time >= min_duration and spectate_count >= 3:
            intervals.append((start_time, end_t))

    logger.info(f"Spectate intervals detected: {len(intervals)} intervals (brightness_max={brightness_max}, stddev_max={stddev_max})")
    return intervals


# ---------------------------------------------------------------------------
# Device detection
# ---------------------------------------------------------------------------

def _get_device() -> str:
    """Phát hiện GPU nếu có, fallback CPU."""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Device detected: {device}")
    if device == "cuda":
        logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
    return device


# ---------------------------------------------------------------------------
# Kill feed OCR (optional — heavy dependency)
# ---------------------------------------------------------------------------

_ocr_reader = None
_ocr_available = None  # Cache trạng thái khả dụng

def _is_ocr_available() -> bool:
    """Kiểm tra EasyOCR có sẵn không (rẻ hơn khởi tạo)."""
    global _ocr_available
    if _ocr_available is None:
        try:
            import easyocr
            _ocr_available = True
        except ImportError:
            _ocr_available = False
            logger.warning("EasyOCR not available, OCR disabled")
    return _ocr_available

def _get_ocr_reader():
    global _ocr_reader
    if _ocr_reader is None and _is_ocr_available():
        try:
            import easyocr
            device = _get_device()
            gpu_enabled = device == "cuda"
            logger.info(f"Initializing EasyOCR with gpu={gpu_enabled}")
            _ocr_reader = easyocr.Reader(["en"], gpu=gpu_enabled)
            logger.info("EasyOCR initialized successfully")
        except Exception as e:
            logger.error(f"EasyOCR initialization failed: {e}")
            _ocr_available = False  # Đánh dấu không khả dụng sau lỗi
            return None
    return _ocr_reader


def _detect_kill_feed(
    video_path: str,
    player_name: str,
    kill_feed_region: list[float],
    sample_interval: float = 2.0,
) -> list[tuple[float, float]]:
    """OCR vùng kill feed, tìm tên tuyển thủ (reduced sample rate).

    kill_feed_region: [x1_ratio, y1_ratio, x2_ratio, y2_ratio] (0-1).
    Returns list of (time_sec, confidence).
    """
    if not player_name:
        logger.info("No player name provided, skipping kill feed OCR")
        return []

    logger.info(f"Detecting kill feed for player: {player_name}")
    
    # Kiểm tra nhanh trước khi khởi tạo
    if not _is_ocr_available():
        logger.info("OCR disabled, skipping kill feed detection")
        return []
        
    reader = _get_ocr_reader()
    if reader is None:
        logger.info("OCR initialization failed, skipping kill feed detection")
        return []

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error(f"Cannot open video for kill feed OCR: {video_path}")
        return []

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_step = max(1, int(fps * max(sample_interval, 10.0)))  # Giảm từ 3s lên 10s cho nhẹ

    logger.info(f"Kill feed OCR: fps={fps:.2f}, total_frames={total_frames}, frame_step={frame_step} (10s min)")

    kills: list[tuple[float, float]] = []
    x1r, y1r, x2r, y2r = kill_feed_region
    player_lower = player_name.lower()

    # Pre-extract all frames into memory first (batch mode)
    frames_batch = []
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
        frames_batch.append((frame_idx, crop))
        
        frame_idx += frame_step
    
    logger.info(f"Pre-extracted {len(frames_batch)} frames for OCR batch processing")
    cap.release()
    
    device = _get_device()
    logger.info(f"OCR device: {device}")
    max_workers_ocr = 4 if device == "cuda" else 2
    logger.info(f"OCR batch processing: {max_workers_ocr} workers on {device}")
    
    ocr_count = 0
    with ThreadPoolExecutor(max_workers=max_workers_ocr) as executor:
        future_to_idx = {}
        
        for frame_idx, crop in frames_batch:
            if reader is None:
                break
            future = executor.submit(reader.readtext, crop, detail=1)
            future_to_idx[future] = frame_idx
        
        for future in as_completed(future_to_idx):
            frame_idx = future_to_idx[future]
            try:
                results = future.result()
                ocr_count += 1
                for bbox, text, conf in results:
                    if player_lower in text.lower():
                        t = frame_idx / fps
                        kills.append((t, conf))
                        logger.debug(f"Kill detected at {t:.2f}s: {text} (conf={conf:.2f})")
                        break
            except Exception as e:
                logger.error(f"OCR error at frame {frame_idx}: {e}")
    logger.info(f"Kill feed OCR complete: {len(kills)} kills found, {ocr_count} frames processed")
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
    """Phát hiện tất cả highlight trong video (parallel processing).

    Kết hợp audio spikes + scene changes + kill feed OCR.
    Gán mỗi highlight vào match tương ứng.

    Args:
        video_path: đường dẫn video
        matches: danh sách Match đã detect
        player_name: tên in-game (cho OCR)
        config: dict config
        progress_cb: callback(progress_0_to_1, status_text)
    """
    logger.info(f"Starting highlight detection: video={video_path}, player={player_name}")
    from config import DEFAULTS
    
    cfg = {**DEFAULTS, **(config or {})}
    pad_before = cfg["highlight_pad_before"]
    pad_after = cfg["highlight_pad_after"]
    min_gap = cfg["highlight_min_gap"]

    logger.info(f"Config: pad_before={pad_before}s, pad_after={pad_after}s, min_gap={min_gap}s")

    if progress_cb:
        progress_cb(0.0, "Đang phân tích audio + scene + spectate...")

    audio_spikes = []
    scene_changes = []
    spectate_intervals = []
    kills = []
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {}
        
        futures['audio'] = executor.submit(
            lambda: _extract_audio_raw(video_path, cfg["ffmpeg_path"])
        )
        futures['scene'] = executor.submit(
            _detect_scene_changes,
            video_path,
            cfg["frame_sample_interval"],
            cfg["scene_change_threshold"],
        )
        
        if cfg.get("death_detect_enabled", True):
            futures['spectate'] = executor.submit(
                _detect_spectate_intervals,
                video_path,
                cfg["spectate_detect_region"],
                cfg["spectate_brightness_max"],
                cfg["spectate_stddev_max"],
                cfg["frame_sample_interval"],
            )
        
        future_to_key = {v: k for k, v in futures.items()}
        for future in as_completed(futures.values()):
            key = future_to_key[future]
            try:
                result = future.result()
                if key == 'audio':
                    samples, sr = result
                    audio_spikes = _detect_audio_spikes(
                        samples, sr, threshold=cfg["audio_spike_threshold"]
                    )
                elif key == 'scene':
                    scene_changes = result
                elif key == 'spectate':
                    spectate_intervals = result
                logger.info(f"Completed: {key} → {len(result) if isinstance(result, (list, tuple)) else 'done'}")
            except Exception as e:
                logger.error(f"Parallel task '{key}' failed: {e}")

    if progress_cb:
        progress_cb(0.75, "Đang đọc kill feed (OCR)...")

    kills = _detect_kill_feed(
        video_path, player_name,
        cfg["kill_feed_region"],
        sample_interval=cfg["frame_sample_interval"],
    )

    if progress_cb:
        progress_cb(0.85, "Đang merge signals...")

    logger.info(f"Detection results: audio_spikes={len(audio_spikes)}, scene_changes={len(scene_changes)}, "
                f"spectate_intervals={len(spectate_intervals)}, kills={len(kills)}")

    cap = cv2.VideoCapture(video_path)
    total_duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / max(cap.get(cv2.CAP_PROP_FPS), 1)
    cap.release()

    num_bins = int(total_duration) + 1
    scores = np.zeros(num_bins, dtype=np.float32)
    types = [""] * num_bins

    for t, s in audio_spikes:
        idx = int(t)
        if 0 <= idx < num_bins:
            scores[idx] += s * 0.4
            types[idx] = "audio_spike"

    if scene_changes:
        max_sc = max(s for _, s in scene_changes)
        for t, s in scene_changes:
            idx = int(t)
            if 0 <= idx < num_bins:
                scores[idx] += (s / max_sc) * 0.3
                if not types[idx]:
                    types[idx] = "scene_change"

    for t, s in kills:
        idx = int(t)
        if 0 <= idx < num_bins:
            scores[idx] += s * 0.5
            types[idx] = "kill"

    combined_threshold = 0.3
    raw_highlights: list[tuple[float, float, float, str]] = []

    for i in range(num_bins):
        if scores[i] >= combined_threshold:
            raw_highlights.append((float(i), scores[i], scores[i], types[i] or "mixed"))

    kill_highlights: list[tuple[float, float, float, str]] = []
    for start, conf, _, htype in raw_highlights:
        if htype == "kill":
            kill_start = max(0, start - 10.0)
            kill_highlights.append((kill_start, conf, conf, "kill"))
        else:
            kill_highlights.append((start, conf, conf, htype))

    logger.info(f"Raw highlights before merge: {len(kill_highlights)}")
    merged = _merge_nearby(kill_highlights, min_gap, pad_before, pad_after, total_duration)
    logger.info(f"Highlights after merge: {len(merged)}")

    highlights: list[Highlight] = []

    for spec_start, spec_end in spectate_intervals:
        mi = _find_match_index(spec_start, matches)
        highlights.append(Highlight(
            start_time=spec_start,
            end_time=spec_end,
            confidence=0.9,
            highlight_type="death",
            match_index=mi,
            label=f"\u2620\ufe0f Death (spectate {spec_end - spec_start:.0f}s)",
        ))

    for start, end, conf, htype in merged:
        mi = _find_match_index(start, matches)
        hl = Highlight(
            start_time=start,
            end_time=end,
            confidence=min(conf, 1.0),
            highlight_type=htype,
            match_index=mi,
        )
        for spec_start, spec_end in spectate_intervals:
            if start >= spec_start and end <= spec_end:
                hl.enabled = False
                hl.label = f"[Spectate] {hl.label or hl.highlight_type}"
                break
        highlights.append(hl)

    highlights.sort(key=lambda h: h.start_time)

    logger.info(f"Highlight detection complete: {len(highlights)} total highlights")
    for i, h in enumerate(highlights):
        logger.debug(f"  [{i}] {h.start_time:.1f}-{h.end_time:.1f}s ({h.highlight_type}, conf={h.confidence:.2f})")

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
