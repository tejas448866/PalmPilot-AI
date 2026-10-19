"""Tests for paced, diversity-aware automatic dataset capture."""

import pytest

from src.ml import CaptureState, DatasetCapturePolicy


def test_capture_interval_is_measured_from_accepted_sample() -> None:
    policy = DatasetCapturePolicy(capture_interval_seconds=0.9)
    features = (0.0, 0.1, 0.2)
    assert policy.evaluate(features, 10.0).ready
    policy.mark_accepted(features, 10.0)
    decision = policy.evaluate((0.2, 0.3, 0.4), 10.5)
    assert decision.state is CaptureState.WAITING
    assert decision.seconds_remaining == pytest.approx(0.4)
    assert policy.evaluate((0.2, 0.3, 0.4), 10.9).ready


def test_near_duplicate_pose_is_rejected_after_interval() -> None:
    policy = DatasetCapturePolicy(capture_interval_seconds=0.9, minimum_feature_distance=0.02)
    features = (0.1, 0.2, 0.3)
    policy.mark_accepted(features, 1.0)
    decision = policy.evaluate((0.101, 0.201, 0.301), 2.0)
    assert decision.state is CaptureState.TOO_SIMILAR
    assert decision.feature_distance is not None
    assert decision.feature_distance < 0.02


def test_sufficient_pose_variation_is_accepted() -> None:
    policy = DatasetCapturePolicy(capture_interval_seconds=0.9, minimum_feature_distance=0.02)
    policy.mark_accepted((0.1, 0.2, 0.3), 1.0)
    decision = policy.evaluate((0.2, 0.35, 0.5), 2.0)
    assert decision.state is CaptureState.READY
    assert decision.feature_distance is not None
    assert decision.feature_distance >= 0.02
