"""Aspect-ratio preserving full-frame preprocessing."""

import time
from dataclasses import dataclass
from typing import Any

from src.exceptions import CameraError


@dataclass(frozen=True)
class ProcessedFrame:
    """Full display frame and optional reduced detector image."""

    bgr: Any
    rgb: Any
    timestamp: float
    processing_size: tuple[int, int]


class FrameProcessor:
    """Mirror the full frame and create a reduced, uncropped detector copy."""

    def __init__(
        self, flip_horizontal: bool = True, processing_size: tuple[int, int] | None = None
    ) -> None:
        self.flip_horizontal = flip_horizontal
        self.processing_size = processing_size

    def process(self, frame: Any) -> ProcessedFrame:
        """Preserve the full display frame; resize only the MediaPipe copy."""
        import cv2

        if frame is None or not getattr(frame, "size", 0):
            raise CameraError("Received an invalid empty frame")
        bgr = cv2.flip(frame, 1) if self.flip_horizontal else frame
        detector_bgr = (
            cv2.resize(bgr, self.processing_size, interpolation=cv2.INTER_AREA)
            if self.processing_size
            else bgr
        )
        rgb = cv2.cvtColor(detector_bgr, cv2.COLOR_BGR2RGB)
        size = (int(detector_bgr.shape[1]), int(detector_bgr.shape[0]))
        return ProcessedFrame(bgr, rgb, time.perf_counter(), size)


def scale_preview(frame: Any, scale: float) -> Any:
    """Resize the complete preview without crop or aspect-ratio distortion."""
    if scale == 1.0:
        return frame
    if scale <= 0:
        raise ValueError("preview scale must be positive")
    import cv2

    height, width = frame.shape[:2]
    return cv2.resize(
        frame,
        (max(1, round(width * scale)), max(1, round(height * scale))),
        interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR,
    )
