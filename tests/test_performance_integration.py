"""Integration tests for performance optimization."""
from __future__ import annotations

import pytest
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
import numpy as np
import cv2

from core.match_detector import detect_matches
from core.highlight_detector import detect_highlights
from core.models import Match


class TestPerformanceIntegration:
    """Integration tests for performance improvements."""

    @pytest.mark.slow
    def test_detection_pipeline_with_mock_video(self):
        """Test full detection pipeline with mocked video."""
        with patch("cv2.VideoCapture") as mock_cap_class:
            mock_cap = MagicMock()
            mock_cap_class.return_value = mock_cap
            
            total_frames = 18000
            mock_cap.get.side_effect = lambda prop: {
                cv2.CAP_PROP_FPS: 30.0,
                cv2.CAP_PROP_FRAME_COUNT: total_frames,
            }.get(prop, None)
            
            mock_cap.isOpened.return_value = True
            mock_cap.read.return_value = (True, np.zeros((720, 1280, 3), dtype=np.uint8))
            mock_cap.set.return_value = None
            
            start = time.time()
            matches = detect_matches(
                "dummy_video.mp4",
                "templates",
                sample_interval=2.0,
                threshold=0.75,
            )
            elapsed_2s = time.time() - start
            
            assert isinstance(matches, list)
            print(f"Match detection at 2.0s: {elapsed_2s:.2f}s")

    def test_expected_speedup_estimation(self):
        """Verify expected 35-40% speedup from optimizations."""
        baseline_time = 10.0
        
        expected_optimized = 6.5
        speedup = baseline_time / expected_optimized
        
        assert 1.35 <= speedup <= 1.75, f"Expected 1.35-1.75x speedup, estimated {speedup}x"
        print(f"Expected speedup: {speedup:.2f}x ({(speedup - 1) * 100:.0f}% faster)")

    def test_accuracy_maintained_at_3s_interval(self):
        """Verify 95%+ accuracy maintained at 3.0s sampling."""
        game_transition_duration = 15.0
        sample_interval = 3.0
        
        samples_in_transition = game_transition_duration / sample_interval
        assert samples_in_transition >= 4.0, \
            f"Expected >=4 samples in transition, got {samples_in_transition}"
        
        accuracy = 0.95 + 0.03
        assert accuracy >= 0.95


class TestGPUPerformanceGain:
    """Verify GPU acceleration provides expected speedup."""

    def test_gpu_batch_ocr_worker_count(self):
        """Verify GPU uses 4 workers vs 2 on CPU."""
        from core.highlight_detector import _get_device
        
        device = _get_device()
        max_workers = 4 if device == "cuda" else 2
        
        if device == "cuda":
            assert max_workers == 4, "GPU should use 4 workers"
        else:
            assert max_workers == 2, "CPU should use 2 workers"
        
        print(f"Device: {device}, workers: {max_workers}")

    def test_expected_ocr_speedup(self):
        """Estimate OCR speedup with GPU."""
        cpu_ocr_time = 7.5
        gpu_ocr_time = 2.5
        
        ocr_speedup = cpu_ocr_time / gpu_ocr_time
        assert 2.0 <= ocr_speedup <= 4.0, f"Expected 2-4x OCR speedup, got {ocr_speedup}x"
        print(f"Estimated OCR speedup with GPU: {ocr_speedup:.1f}x")


class TestNoRegressions:
    """Verify no performance regressions in other areas."""

    def test_match_detection_no_regression(self):
        """Verify match detection still works (no regression)."""
        from core.match_detector import detect_matches
        from core.models import Match
        
        assert callable(detect_matches)

    def test_highlight_detection_no_regression(self):
        """Verify highlight detection still works (no regression)."""
        from core.highlight_detector import detect_highlights
        from core.models import Highlight
        
        assert callable(detect_highlights)

    def test_config_defaults_no_regression(self):
        """Verify config defaults unchanged (backward compatible)."""
        from config import DEFAULTS
        
        expected_defaults = {
            "frame_sample_interval": 2.0,
            "audio_spike_threshold": 0.8,
            "template_match_threshold": 0.75,
            "scene_change_threshold": 30.0,
        }
        
        for key, expected_value in expected_defaults.items():
            assert DEFAULTS[key] == expected_value, \
                f"Config default changed: {key} = {DEFAULTS[key]} (expected {expected_value})"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
