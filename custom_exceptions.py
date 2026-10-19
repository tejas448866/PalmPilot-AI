"""Application-specific error types."""


class ApplicationError(Exception):
    """Base error for expected application failures."""


class ConfigurationError(ApplicationError):
    """Configuration is missing or invalid."""


class CameraError(ApplicationError):
    """Camera operation failed."""


class CameraNotAvailableError(CameraError):
    """The selected camera could not be opened."""


class CalibrationError(ApplicationError):
    """Calibration data is invalid or unavailable."""


class HandTrackingError(ApplicationError):
    """Hand tracking failed."""


class ControllerError(ApplicationError):
    """Keyboard controller operation failed."""


class InvalidKeyMappingError(ControllerError):
    """A configured key name is unsupported."""


class RecordingError(ApplicationError):
    """Video recording could not be initialized."""
