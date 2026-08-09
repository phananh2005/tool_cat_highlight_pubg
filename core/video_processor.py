"""Cắt và ghép video bằng FFmpeg subprocess.

Dùng stream copy (-c copy) mặc định cho tốc độ.
Fallback re-encode nếu cần seek chính xác.
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Callable, Optional

from core.models import Highlight


def cut_clip(
    source: str,
    start: float,
    end: float,
    output: str,
    ffmpeg: str = "ffmpeg",
    accurate: bool = False,
    fps: int | None = None,
) -> bool:
    """Cắt 1 clip từ source video.

    Args:
        accurate: True = re-encode cho seek chính xác (chậm hơn)
        fps: Output FPS (None = giữ fps gốc)
    """
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    duration = end - start

    if accurate:
        cmd = [
            ffmpeg, "-y",
            "-ss", f"{start:.3f}",
            "-i", source,
            "-t", f"{duration:.3f}",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k",
        ]
        if fps:
            cmd.extend(["-r", str(fps)])
        cmd.append(output)
    else:
        cmd = [
            ffmpeg, "-y",
            "-ss", f"{start:.3f}",
            "-i", source,
            "-t", f"{duration:.3f}",
        ]
        if fps:
            cmd.extend(["-r", str(fps)])
        cmd.extend([
            "-c", "copy",
            "-avoid_negative_ts", "make_zero",
            output,
        ])

    result = subprocess.run(
        cmd, capture_output=True, timeout=300,
    )
    return result.returncode == 0


def merge_clips(
    clip_paths: list[str],
    output: str,
    ffmpeg: str = "ffmpeg",
) -> bool:
    """Ghép nhiều clip thành 1 video bằng concat demuxer."""
    if not clip_paths:
        return False

    Path(output).parent.mkdir(parents=True, exist_ok=True)

    # Tạo file list tạm
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as f:
        for p in clip_paths:
            # Escape single quotes trong path
            safe = p.replace("'", "'\\''")
            f.write(f"file '{safe}'\n")
        list_path = f.name

    try:
        cmd = [
            ffmpeg, "-y",
            "-f", "concat", "-safe", "0",
            "-i", list_path,
            "-c", "copy",
            output,
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=600)
        return result.returncode == 0
    finally:
        Path(list_path).unlink(missing_ok=True)


def export_highlights(
    source: str,
    highlights: list[Highlight],
    output_dir: str,
    group_label: str = "game",
    ffmpeg: str = "ffmpeg",
    accurate: bool = False,
    merge: bool = False,
    fps: int | None = None,
    progress_cb: Optional[Callable[[float, str], None]] = None,
) -> list[str]:
    """Export highlights — riêng lẻ + tùy chọn gộp.

    Returns: list đường dẫn file đã tạo.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    enabled = [h for h in highlights if h.enabled]
    if not enabled:
        return []

    created: list[str] = []
    total = len(enabled)

    for i, h in enumerate(enabled):
        label = h.label or f"highlight_{i + 1:03d}"
        # Sanitize filename
        safe_label = "".join(c if c.isalnum() or c in "-_ " else "_" for c in label).strip()
        clip_name = f"{group_label}_{safe_label}.mp4"
        clip_path = str(out / clip_name)

        ok = cut_clip(source, h.start_time, h.end_time, clip_path, ffmpeg, accurate, fps)
        if ok:
            created.append(clip_path)

        if progress_cb:
            progress_cb((i + 1) / (total + (1 if merge else 0)), f"Cắt {clip_name}...")

    # Gộp nếu được yêu cầu
    if merge and len(created) > 1:
        merged_path = str(out / f"{group_label}_merged.mp4")
        if progress_cb:
            progress_cb(0.95, f"Gộp {group_label}...")
        ok = merge_clips(created, merged_path, ffmpeg)
        if ok:
            created.append(merged_path)

    if progress_cb:
        progress_cb(1.0, "Hoàn tất export.")

    return created
