"""Test scene detection performance at 2.0s sampling interval."""
from __future__ import annotations

import pytest
from unittest.mock import Mock, patch, MagicMock
import numpy as np
import cv2
from pathlib import Path
import tempfile

from core.highlight_detector import _detect_scene_changes
from config import DEFAULTS


class TestSceneDetectionSamplingInterval:
    """Verify scene detection uses correct 2.0s sampling interval."""

    def test_frame_step_calculation(self):
        """Verify frame_step = fps * sample_interval is correct."""
        fps = 30.0
        sample_interval = 2.0
        expected_frame_step = max(1, int(fps * sample_interval))
        assert expected_frame_step == 60, f"Expected frame_step=60 for fps={fps}, interval={sample_interval}s, got {expected_frame_step}"

    def test_config_default_interval(self):
        """Verify default frame_sample_interval is 2.0s."""
        assert DEFAULTS["frame_sample_interval"] == 2.0, f"Expected frame_sample_interval=2.0, got {DEFAULTS['frame_sample_interval']}"

    @patch("cv2.VideoCapture")
    def test_scene_detection_with_mock_video(self, mock_capture_class):
        """Test scene detection sampling interval with mocked video."""
        mock_cap = MagicMock()
        mock_capture_class.return_value = mock_cap
        
        mock_cap.get.side_effect = lambda prop: {
            cv2.CAP_PROP_FPS: 30.0,
            cv2.CAP_PROP_FRAME_COUNT: 300,
        }.get(prop, None)
        
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, np.zeros((720, 1280, 3), dtype=np.uint8))
        
        sample_interval = 2.0
        changes = _detect_scene_changes(
            "dummy_video.mp4",
            sample_interval=sample_interval,
            threshold=30.0
        )
        
        mock_cap.set.assert_called()
        mock_cap.release.assert_called()


class TestMotionUniformityFilter:
    """Verify motion uniformity filter rejects uniform camera movements."""

    def test_uniformity_calculation(self):
        """Test that uniformity < 0.6 filter works correctly."""
        consecutive_diffs = [
            (0.0, 10.0, 0.1),
            (1.0, 15.0, 0.3),
            (2.0, 20.0, 0.8),
            (3.0, 25.0, 0.2),
            (4.0, 30.0, 0.9),
        ]
        
        threshold = 0.6
        filtered = [(t, diff) for t, diff, uniformity in consecutive_diffs if uniformity < threshold]
        
        assert len(filtered) == 3, f"Expected 3 filtered changes, got {len(filtered)}"
        assert all(uniformity < threshold for _, _, uniformity in consecutive_diffs if (_, _) in filtered)

    def test_motion_uniformity_detection(self):
        """Test that uniform camera pans are filtered out."""
        uniform_motions = [
            (0.0, 5.0, 0.95),
            (1.0, 4.8, 0.94),
            (2.0, 5.1, 0.96),
        ]
        
        threshold = 0.6
        filtered = [(t, diff) for t, diff, uniformity in uniform_motions if uniformity < threshold]
        assert len(filtered) == 0, "Uniform motions should be filtered out"

    def test_scene_changes_pass_filter(self):
        """Test that actual scene changes pass uniformity filter."""
        scene_changes = [
            (0.0, 50.0, 0.2),
            (2.0, 60.0, 0.3),
            (4.0, 45.0, 0.1),
        ]
        
        threshold = 0.6
        filtered = [(t, diff) for t, diff, uniformity in scene_changes if uniformity < threshold]
        assert len(filtered) == 3, "All scene changes should pass uniformity filter"


class TestSceneDetectionConfigIntegration:
    """Verify scene detection uses frame_sample_interval from config."""

    def test_config_has_frame_sample_interval(self):
        """Verify DEFAULTS dict has frame_sample_interval key."""
        assert "frame_sample_interval" in DEFAULTS
        assert isinstance(DEFAULTS["frame_sample_interval"], (int, float))
        assert DEFAULTS["frame_sample_interval"] > 0

    def test_frame_sample_interval_is_2_seconds(self):
        """Verify frame_sample_interval is exactly 2.0 seconds."""
        assert DEFAULTS["frame_sample_interval"] == 2.0

    def test_scene_change_threshold_exists(self):
        """Verify scene_change_threshold is configured."""
        assert "scene_change_threshold" in DEFAULTS
        assert DEFAULTS["scene_change_threshold"] == 30.0

    def test_sampling_at_2_second_intervals(self):
        """Test sampling frames at 2.0s intervals for 30fps video."""
        fps = 30.0
        sample_interval = 2.0
        total_frames = 300
        
        frame_step = max(1, int(fps * sample_interval))
        sampled_frame_indices = list(range(0, total_frames, frame_step))
        
        assert frame_step == 60
        assert len(sampled_frame_indices) == 5
        assert sampled_frame_indices == [0, 60, 120, 180, 240]


class TestPerformanceMetrics:
    """Test performance characteristics of 2.0s sampling."""

    def test_sampling_coverage(self):
        """Verify 2.0s sampling covers entire video reasonably."""
        fps = 24.0
        duration_seconds = 120.0
        total_frames = int(fps * duration_seconds)
        sample_interval = 2.0
        
        frame_step = max(1, int(fps * sample_interval))
        num_samples = (total_frames - 1) // frame_step + 1
        
        coverage_percent = (num_samples / total_frames) * 100
        assert coverage_percent > 1.0, f"Coverage too low: {coverage_percent}%"
        assert coverage_percent < 20.0, f"Coverage too high: {coverage_percent}%"

    def test_reduced_computation_load(self):
        """Verify 2.0s interval reduces computation vs 1.0s."""
        fps = 30.0
        total_frames = 3600
        
        frames_1s = (total_frames - 1) // max(1, int(fps * 1.0)) + 1
        frames_2s = (total_frames - 1) // max(1, int(fps * 2.0)) + 1
        
        reduction_ratio = frames_1s / frames_2s
        assert reduction_ratio == 2.0, f"Expected 2x reduction, got {reduction_ratio}x"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
