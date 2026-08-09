# Task 1: Enable GPU Detection & Batch OCR Processing

## Status
DONE

## Commits
- `ad1f07f` perf: enable GPU batch OCR processing (4 workers on CUDA)

## Changes Summary
1. **Batch Frame Extraction** (lines 331-349): Pre-extract all frames into memory before OCR processing instead of frame-by-frame extraction within ThreadPoolExecutor
2. **GPU Device Detection** (lines 351-354): Call `_get_device()` to detect GPU availability and log device info
3. **Adaptive Worker Count** (line 353): Set `max_workers=4` on CUDA, `max_workers=2` on CPU
4. **Release Video Handle Early** (line 349): Move `cap.release()` before ThreadPoolExecutor to avoid resource contention

## Implementation Details
- `_get_device()` function (already existed at line 280) returns "cuda" if torch.cuda.is_available(), else "cpu"
- Batch extraction stores tuples of (frame_idx, crop) in `frames_batch` list
- ThreadPoolExecutor now processes pre-extracted crops instead of doing frame extraction and OCR concurrently
- Device detection is logged at INFO level for visibility

## Test Summary
No test suite found. Syntax verified with `python -m py_compile`. Imports verified successfully.

## Concerns
None. Changes are minimal, backward compatible, and aligned with requirements:
- GPU detection is optional (fallback to CPU if CUDA unavailable)
- Batch extraction maintains same accuracy (no frame skipping)
- Worker count is adaptive based on device
- Config defaults unchanged
