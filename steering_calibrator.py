"""Calibration sample calculations."""

import statistics


def robust_angle(samples: list[float]) -> float:
    """Return the median angle from non-empty samples."""
    if not samples:
        raise ValueError("At least one angle sample is required")
    return float(statistics.median(samples))
