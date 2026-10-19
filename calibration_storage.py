"""Versioned, validated calibration persistence."""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from src.exceptions import CalibrationError


@dataclass(frozen=True)
class Calibration:
    """User, camera, tracking, steering, and pedal calibration."""

    schema_version: int = 2
    timestamp: str = ""
    camera_index: int = 0
    requested_resolution: tuple[int, int] = (1280, 720)
    actual_resolution: tuple[int, int] = (0, 0)
    preview_flip_horizontal: bool = True
    neutral_angle: float = 0.0
    maximum_left_angle: float = -45.0
    maximum_right_angle: float = 45.0
    dead_zone: float = 5.0
    enter_left_threshold: float = -12.0
    exit_left_threshold: float = -7.0
    enter_right_threshold: float = 12.0
    exit_right_threshold: float = 7.0
    normalized_left_range: float = 45.0
    normalized_right_range: float = 45.0
    accelerate_y: float = 0.38
    brake_y: float = 0.68
    invert: bool = False
    reference_point: str = "palm_center"
    persistence_frames: int = 6
    persistence_ms: float = 250.0
    point_smoothing_alpha: float = 0.45

    def validate(self) -> None:
        """Validate schema and physically meaningful ordering."""
        if self.schema_version not in (1, 2):
            raise CalibrationError("Unsupported calibration schema version")
        if self.maximum_left_angle >= self.maximum_right_angle:
            raise CalibrationError("Left calibration angle must be below right angle")
        if not (
            self.maximum_left_angle
            < self.enter_left_threshold
            < self.exit_left_threshold
            < 0
            < self.exit_right_threshold
            < self.enter_right_threshold
            < self.maximum_right_angle
        ):
            raise CalibrationError("Steering thresholds are not safely ordered")
        if not 0 <= self.accelerate_y < self.brake_y <= 1:
            raise CalibrationError("Pedal thresholds must satisfy accelerate < brake")
        if self.camera_index < 0 or self.dead_zone <= 0:
            raise CalibrationError("Camera index and dead zone are invalid")
        if self.normalized_left_range <= 0 or self.normalized_right_range <= 0:
            raise CalibrationError("Normalized steering ranges must be positive")

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "Calibration":
        """Load schema 1 or 2 mappings with tuple normalization."""
        migrated = dict(data)
        migrated.setdefault("schema_version", 1)
        for key in ("requested_resolution", "actual_resolution"):
            if key in migrated:
                migrated[key] = tuple(map(int, migrated[key]))
        calibration = cls(**migrated)
        calibration.validate()
        return calibration


def load_calibration(path: Path | None) -> Calibration:
    """Load calibration or return safe defaults when missing."""
    if path is None or not path.exists():
        return Calibration()
    try:
        data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return Calibration.from_mapping(data)
    except (TypeError, ValueError, OSError, yaml.YAMLError) as exc:
        raise CalibrationError(f"Invalid calibration file {path}: {exc}") from exc


def save_calibration(path: Path, calibration: Calibration, force: bool = False) -> None:
    """Save a validated calibration, refusing accidental overwrite."""
    if path.exists() and not force:
        raise CalibrationError(f"{path} exists; pass --force to overwrite")
    calibration.validate()
    data = asdict(calibration)
    data["timestamp"] = calibration.timestamp or datetime.now(timezone.utc).isoformat()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
