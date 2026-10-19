"""Apply stored calibration values to runtime configuration."""

from typing import Any

from .calibration_storage import Calibration


def apply_calibration(config: dict[str, Any], calibration: Calibration) -> None:
    """Mutate a loaded runtime configuration with explicit calibration."""
    config["steering"].update(
        {
            "neutral_angle": calibration.neutral_angle,
            "maximum_angle": max(
                abs(calibration.maximum_left_angle), abs(calibration.maximum_right_angle)
            ),
            "normalized_left_range": calibration.normalized_left_range,
            "normalized_right_range": calibration.normalized_right_range,
            "dead_zone": calibration.dead_zone,
            "enter_left_threshold": calibration.enter_left_threshold,
            "exit_left_threshold": calibration.exit_left_threshold,
            "enter_right_threshold": calibration.enter_right_threshold,
            "exit_right_threshold": calibration.exit_right_threshold,
            "invert": calibration.invert,
        }
    )
    config["gestures"]["thresholds"].update(
        {
            "accelerate_y": calibration.accelerate_y,
            "brake_y": calibration.brake_y,
        }
    )
    config["camera"]["index"] = calibration.camera_index
    config["hand_tracking"].update(
        {
            "reference_point": calibration.reference_point,
            "persistence_frames": calibration.persistence_frames,
            "persistence_ms": calibration.persistence_ms,
            "point_smoothing_alpha": calibration.point_smoothing_alpha,
        }
    )
