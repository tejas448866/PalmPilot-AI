"""Robust calibration aggregation and safe threshold derivation."""

import statistics
from dataclasses import dataclass

from src.exceptions import CalibrationError
from src.utils.geometry import clamp, normalize_angle


def robust_median(samples: list[float], minimum_samples: int = 10) -> float:
    """Return a median after rejecting non-finite and unstable samples."""
    import math

    clean = [float(value) for value in samples if math.isfinite(value)]
    if len(clean) < minimum_samples:
        raise CalibrationError(f"Need at least {minimum_samples} valid samples")
    median = float(statistics.median(clean))
    deviations = [abs(value - median) for value in clean]
    mad = float(statistics.median(deviations))
    filtered = [value for value in clean if abs(value - median) <= max(1.5, 3.5 * mad)]
    if len(filtered) < minimum_samples:
        raise CalibrationError("Samples are too unstable; hold the gesture steady and retry")
    return float(statistics.median(filtered))


@dataclass(frozen=True)
class DerivedSteering:
    """Safe calibration-derived steering parameters."""

    neutral_angle: float
    calibrated_left_angle: float
    calibrated_right_angle: float
    dead_zone: float
    enter_left_threshold: float
    exit_left_threshold: float
    enter_right_threshold: float
    exit_right_threshold: float
    normalized_left_range: float
    normalized_right_range: float


def derive_steering(
    neutral_samples: list[float],
    left_samples: list[float],
    right_samples: list[float],
    invert: bool = False,
    minimum_samples: int = 10,
) -> DerivedSteering:
    """Aggregate steering poses and derive ordered hysteresis thresholds."""
    neutral = robust_median(neutral_samples, minimum_samples)
    left_raw = robust_median(left_samples, minimum_samples)
    right_raw = robust_median(right_samples, minimum_samples)
    left = normalize_angle(left_raw - neutral)
    right = normalize_angle(right_raw - neutral)
    if invert:
        left, right = -left, -right
    if left >= -10 or right <= 10:
        raise CalibrationError("Left and right poses must be at least 10 degrees from neutral")
    if left >= right:
        raise CalibrationError("Calibrated steering direction is inverted or ambiguous")
    smaller_range = min(abs(left), right)
    dead_zone = clamp(smaller_range * 0.12, 3.0, 7.0)
    enter_left = -max(dead_zone + 3.0, abs(left) * 0.30)
    enter_right = max(dead_zone + 3.0, right * 0.30)
    exit_left = -max(dead_zone, abs(enter_left) * 0.58)
    exit_right = max(dead_zone, enter_right * 0.58)
    if not (left < enter_left < exit_left < 0 < exit_right < enter_right < right):
        raise CalibrationError("Derived hysteresis thresholds are unsafe")
    return DerivedSteering(
        neutral,
        left,
        right,
        dead_zone,
        enter_left,
        exit_left,
        enter_right,
        exit_right,
        abs(left),
        right,
    )


def derive_pedal_thresholds(
    acceleration_samples: list[float],
    brake_samples: list[float],
    minimum_samples: int = 10,
) -> tuple[float, float]:
    """Derive separated vertical-region thresholds from stable hand-height samples."""
    acceleration_pose = robust_median(acceleration_samples, minimum_samples)
    brake_pose = robust_median(brake_samples, minimum_samples)
    if not 0 <= acceleration_pose < brake_pose <= 1:
        raise CalibrationError("Acceleration pose must be above the brake pose")
    separation = brake_pose - acceleration_pose
    if separation < 0.15:
        raise CalibrationError("Pedal poses are too close; use more vertical separation")
    margin = min(0.08, separation * 0.2)
    return acceleration_pose + margin, brake_pose - margin
