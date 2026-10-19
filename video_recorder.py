"""Optional OpenCV video recording."""

from datetime import datetime
from pathlib import Path
from typing import Any, Protocol, cast

from src.exceptions import RecordingError


class _OpenCVFourCC(Protocol):
    """Narrow OpenCV surface needed for codec construction."""

    @staticmethod
    def VideoWriter_fourcc(c1: str, c2: str, c3: str, c4: str) -> int:
        """Construct an OpenCV FOURCC integer."""
        ...


class VideoRecorder:
    """Own an OpenCV VideoWriter with safe lazy startup."""

    def __init__(self, output_directory: Path, codec: str, fps: float) -> None:
        self.output_directory = output_directory
        self.codec = codec
        self.fps = fps
        self.writer: Any | None = None
        self.path: Path | None = None

    def start(self, frame_size: tuple[int, int]) -> Path:
        """Create a timestamped writer."""
        import cv2

        self.output_directory.mkdir(parents=True, exist_ok=True)
        self.path = self.output_directory / f"session_{datetime.now():%Y%m%d_%H%M%S}.mp4"
        typed_cv2 = cast(_OpenCVFourCC, cv2)
        fourcc = typed_cv2.VideoWriter_fourcc(*self.codec)
        self.writer = cv2.VideoWriter(str(self.path), fourcc, self.fps, frame_size)
        if not self.writer.isOpened():
            self.writer.release()
            self.writer = None
            raise RecordingError(f"Could not open video writer at {self.path}")
        return self.path

    @property
    def active(self) -> bool:
        """Whether frames can be written."""
        return self.writer is not None

    def write(self, frame: Any) -> None:
        """Write one frame if active."""
        if self.writer is not None:
            self.writer.write(frame)

    def stop(self) -> None:
        """Release writer safely."""
        if self.writer is not None:
            self.writer.release()
            self.writer = None
