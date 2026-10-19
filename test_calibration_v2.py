"""Robust Version 2 calibration math and schema tests."""

import pytest

from src.calibration import derive_pedal_thresholds, derive_steering, robust_median
from src.exceptions import CalibrationError
from src.gesture.steering_detector import normalize_steering_value


def test_robust_median_rejects_outlier() -> None:
    samples = [10.0, 10.1, 9.9, 10.2, 9.8, 10.0, 10.1, 9.9, 10.0, 500.0]
    assert robust_median(samples, 9) == pytest.approx(10.0)


def test_invalid_samples_and_poses_are_rejected() -> None:
    with pytest.raises(CalibrationError):
        robust_median([1.0], 3)
    with pytest.raises(CalibrationError):
        derive_pedal_thresholds([0.5] * 10, [0.55] * 10)


def test_derived_threshold_order_and_asymmetric_normalization() -> None:
    derived = derive_steering([2.0] * 10, [-38.0] * 10, [52.0] * 10)
    assert (
        derived.calibrated_left_angle
        < derived.enter_left_threshold
        < derived.exit_left_threshold
        < 0
        < derived.exit_right_threshold
        < derived.enter_right_threshold
        < derived.calibrated_right_angle
    )
    assert normalize_steering_value(-40, 40, 50) == -1
    assert normalize_steering_value(50, 40, 50) == 1
    assert normalize_steering_value(25, 40, 50) == 0.5
