"""Public exception types."""

from .custom_exceptions import (
    ApplicationError,
    CalibrationError,
    CameraError,
    CameraNotAvailableError,
    ConfigurationError,
    ControllerError,
    HandTrackingError,
    InvalidKeyMappingError,
    RecordingError,
)

__all__ = [
    "ApplicationError",
    "CalibrationError",
    "CameraError",
    "CameraNotAvailableError",
    "ConfigurationError",
    "ControllerError",
    "HandTrackingError",
    "InvalidKeyMappingError",
    "RecordingError",
]
