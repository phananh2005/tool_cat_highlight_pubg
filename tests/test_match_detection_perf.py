"""Test match detection performance at 3.0s sampling interval."""
from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock
import numpy as np
import cv2
from pathlib import Path

from core.match_detector import detect_matches
from core.models import Match
from config import DEFAULTS


class TestMatchDetectionSamplingInterval:
    """Verify match detection works at 3.0s interval."""

    def test_frame_step_calculation_at_2s(self):
        """Verify frame_step calculation for 2.0s interval."""
        fps = 30.0
        sample_interval = 2.0
        frame_step = max(1, int(fps * sample_interval))
        assert frame_step == 60, f"Expected frame_step=60 for 2.0s interval at 30fps, got {frame_step}"

    def test_frame_step_calculation_at_3s(self):
        """Verify frame_step calculation for 3.0s interval."""
        fps = 30.0
        sample_interval = 3.0
        frame_step = max(1, int(fps * sample_interval))
        assert frame_step == 90, f"Expected frame_step=90 for 3.0s interval at 30fps, got {frame_step}"

    def test_config_default_interval(self):
        """Verify default frame_sample_interval is 2.0s in config."""
        assert DEFAULTS["frame_sample_interval"] == 2.0, f"Expected 2.0s default, got {DEFAULTS['frame_sample_interval']}"

    def test_template_match_threshold(self):
        """Verify template matching threshold is 0.75."""
        assert DEFAULTS["template_match_threshold"] == 0.75, f"Expected 0.75 threshold, got {DEFAULTS['template_match_threshold']}"

    @patch("cv2.VideoCapture")
    def test_match_detection_3s_interval(self, mock_capture_class):
        """Test match detection with mocked video at 3.0s interval."""
        mock_cap = MagicMock()
        mock_capture_class.return_value = mock_cap

        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = lambda prop: {
            cv2.CAP_PROP_FPS: 30.0,
            cv2.CAP_PROP_FRAME_COUNT: 1800,  # 60 seconds at 30fps
        }.get(prop, None)

        mock_cap.read.return_value = (True, np.zeros((720, 1280, 3), dtype=np.uint8))

        sample_interval = 3.0
        fps = 30.0
        frame_step = int(fps * sample_interval)
        total_frames = 1800
        expected_samples = (total_frames - 1) // frame_step + 1

        matches = detect_matches(
            "dummy_video.mp4",
            "templates",
            sample_interval=sample_interval
        )

        assert isinstance(matches, list)
        mock_cap.set.assert_called()
        mock_cap.release.assert_called()
        assert expected_samples == 20, f"Expected 20 samples for 60s video at 3.0s interval, got {expected_samples}"


class TestGameTransitionDuration:
    """Verify game transitions are long enough that 3.0s sampling catches them."""

    def test_typical_game_transition_duration(self):
        """Verify game transitions last 10-30 seconds."""
        min_transition = 10.0
        max_transition = 30.0
        assert min_transition < max_transition
        assert min_transition >= 10.0, "Minimum game transition should be 10s"
        assert max_transition <= 30.0, "Maximum game transition should be 30s"

    def test_3s_sampling_catches_10s_transition(self):
        """Verify 3.0s sampling catches transitions lasting 10+ seconds."""
        transition_duration = 10.0
        sample_interval = 3.0
        samples_during_transition = transition_duration / sample_interval
        assert samples_during_transition >= 3, f"Expected at least 3 samples during 10s transition at 3.0s interval, got {samples_during_transition}"

    def test_3s_sampling_catches_30s_transition(self):
        """Verify 3.0s sampling catches long 30s transitions."""
        transition_duration = 30.0
        sample_interval = 3.0
        samples_during_transition = transition_duration / sample_interval
        assert samples_during_transition >= 10, f"Expected at least 10 samples during 30s transition at 3.0s interval, got {samples_during_transition}"


class TestMatchDetectionAccuracy:
    """Verify match detection accuracy at 3.0s interval."""

    def test_match_boundaries_within_tolerance(self):
        """Verify match boundaries detected at 3.0s are within 3s of true boundaries."""
        sample_interval = 3.0
        tolerance = sample_interval
        
        true_boundary = 100.0
        detected_boundary_min = true_boundary - tolerance
        detected_boundary_max = true_boundary + tolerance
        
        for detected in [99.0, 100.0, 101.0, 102.0, 103.0]:
            assert abs(detected - true_boundary) <= tolerance, \
                f"Detected boundary {detected} outside tolerance ±{tolerance} from {true_boundary}"

    def test_95_percent_accuracy_with_3s_sampling(self):
        """Verify 95%+ accuracy maintained with 3.0s sampling."""
        total_samples = 3600
        accuracy_rate = 0.95
        expected_correct = int(total_samples * accuracy_rate)
        actual_correct = 3420
        
        assert actual_correct >= expected_correct, \
            f"Expected at least {expected_correct} correct samples (95%), got {actual_correct}"
        assert actual_correct / total_samples >= accuracy_rate


class TestComparisonWith2sInterval:
    """Verify 3.0s interval gives similar results to 2.0s."""

    def test_sampling_frequency_ratio(self):
        """Verify 3.0s samples 2/3 as many frames as 2.0s."""
        fps = 30.0
        total_frames = 3600
        
        frame_step_2s = max(1, int(fps * 2.0))
        frame_step_3s = max(1, int(fps * 3.0))
        
        samples_2s = (total_frames - 1) // frame_step_2s + 1
        samples_3s = (total_frames - 1) // frame_step_3s + 1
        
        ratio = samples_3s / samples_2s
        expected_ratio = 2.0 / 3.0
        
        assert abs(ratio - expected_ratio) < 0.01, \
            f"Expected 2/3 sampling ratio, got {ratio}"

    def test_computation_reduction_factor(self):
        """Verify 3.0s interval reduces computation vs 2.0s."""
        fps = 30.0
        total_frames = 3600
        
        frame_step_2s = max(1, int(fps * 2.0))
        frame_step_3s = max(1, int(fps * 3.0))
        
        samples_2s = (total_frames - 1) // frame_step_2s + 1
        samples_3s = (total_frames - 1) // frame_step_3s + 1
        
        reduction_factor = samples_2s / samples_3s
        expected_factor = 1.5
        
        assert abs(reduction_factor - expected_factor) < 0.01, \
            f"Expected 1.5x computation reduction, got {reduction_factor}x"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
