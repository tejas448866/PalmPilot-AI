"""Timestamped screenshot output."""

from datetime import datetime
from pathlib import Path
from typing import Any


class ScreenshotManager:
    """Save frames beneath a configured directory."""

    def __init__(self, output_directory: Path) -> None:
        self.output_directory = output_directory

    def save(self, frame: Any) -> Path:
        """Save a PNG or raise when OpenCV reports failure."""
        import cv2

        self.output_directory.mkdir(parents=True, exist_ok=True)
        path = self.output_directory / f"screenshot_{datetime.now():%Y%m%d_%H%M%S_%f}.png"
        if not cv2.imwrite(str(path), frame):
            raise OSError(f"Could not save screenshot to {path}")
        return path
