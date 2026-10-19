"""Full-frame OpenCV camera acquisition with Windows backend probing."""

import logging
from dataclasses import dataclass
from typing import Any

from src.exceptions import CameraError, CameraNotAvailableError

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class CameraDiagnostics:
    """Capture properties accepted by the camera driver."""

    index: int | str
    backend: str
    requested_resolution: tuple[int, int]
    negotiated_resolution: tuple[int, int]
    actual_resolution: tuple[int, int]
    processing_resolution: tuple[int, int] | None
    preview_resolution: tuple[int, int]


class CameraManager:
    """Probe backends, negotiate a full-frame mode, and own the webcam."""

    def __init__(
        self,
        index: int | str,
        requested_width: int,
        requested_height: int,
        fps: int,
        backend_order: list[str] | None = None,
        fallback_resolutions: list[list[int]] | None = None,
        processing_width: int | None = None,
        preview_scale: float = 1.0,
        warmup_frames: int = 15,
        autofocus: bool | None = None,
        exposure: float | None = None,
        retries: int = 2,
    ) -> None:
        import cv2

        self._cv2 = cv2
        self.retries = retries
        self.capture, backend = self._open_backend(
            index, backend_order or ["dshow", "msmf", "default"]
        )
        resolutions = [(requested_width, requested_height)]
        resolutions.extend((int(item[0]), int(item[1])) for item in (fallback_resolutions or []))
        selected, actual = self._select_resolution(resolutions, fps)
        self._set_optional(cv2.CAP_PROP_AUTOFOCUS, autofocus)
        self._set_optional(cv2.CAP_PROP_EXPOSURE, exposure)
        for _ in range(max(0, warmup_frames)):
            self.capture.read()
        processing = self._processing_resolution(actual, processing_width)
        preview = (
            max(1, round(actual[0] * preview_scale)),
            max(1, round(actual[1] * preview_scale)),
        )
        self.diagnostics = CameraDiagnostics(
            index,
            backend,
            (requested_width, requested_height),
            selected,
            actual,
            processing,
            preview,
        )
        LOGGER.info("Camera diagnostics: %s", self.diagnostics)

    def _open_backend(self, index: int | str, order: list[str]) -> tuple[Any, str]:
        backend_ids = {
            "dshow": self._cv2.CAP_DSHOW,
            "msmf": self._cv2.CAP_MSMF,
            "default": self._cv2.CAP_ANY,
        }
        previous_level = self._cv2.getLogLevel() if hasattr(self._cv2, "getLogLevel") else None
        try:
            if hasattr(self._cv2, "setLogLevel"):
                self._cv2.setLogLevel(2)
            effective_order = ["default"] if isinstance(index, str) else order
            for name in effective_order:
                if name not in backend_ids:
                    LOGGER.warning("Ignoring unknown camera backend %s", name)
                    continue
                capture = self._cv2.VideoCapture(index, backend_ids[name])
                if capture.isOpened():
                    return capture, name
                capture.release()
                LOGGER.debug("Camera %s did not open with backend %s", index, name)
        finally:
            if previous_level is not None:
                self._cv2.setLogLevel(previous_level)
        raise CameraNotAvailableError(
            f"Camera index {index} is unavailable with backends {order}. "
            "Run scripts/check_camera.py."
        )

    def _select_resolution(
        self, resolutions: list[tuple[int, int]], fps: int
    ) -> tuple[tuple[int, int], tuple[int, int]]:
        best: tuple[tuple[int, int], tuple[int, int]] | None = None
        for requested in resolutions:
            self.capture.set(self._cv2.CAP_PROP_FRAME_WIDTH, requested[0])
            self.capture.set(self._cv2.CAP_PROP_FRAME_HEIGHT, requested[1])
            self.capture.set(self._cv2.CAP_PROP_FPS, fps)
            ok, frame = self.capture.read()
            if not ok or frame is None or not frame.size:
                continue
            actual = (int(frame.shape[1]), int(frame.shape[0]))
            best = (requested, actual)
            if actual == requested:
                break
        if best is None:
            raise CameraError("Camera opened but no requested resolution returned a frame")
        return best

    @staticmethod
    def _processing_resolution(
        actual: tuple[int, int], processing_width: int | None
    ) -> tuple[int, int] | None:
        if not processing_width or processing_width >= actual[0]:
            return None
        return processing_width, max(1, round(actual[1] * processing_width / actual[0]))

    def _set_optional(self, property_id: int, value: bool | float | None) -> None:
        if value is None:
            return
        if not self.capture.set(property_id, float(value)):
            LOGGER.debug("Camera driver rejected optional property %s", property_id)

    def read(self) -> Any:
        """Read a complete, uncropped frame with transient retries."""
        for _ in range(self.retries + 1):
            success, frame = self.capture.read()
            if success and frame is not None and frame.size:
                return frame
        raise CameraError("Camera opened but did not return a valid frame")

    @property
    def actual_fps(self) -> float:
        """Return the FPS value currently reported by the driver."""
        return float(self.capture.get(self._cv2.CAP_PROP_FPS))

    def release(self) -> None:
        """Release the capture device."""
        if self.capture is not None:
            self.capture.release()

    def __enter__(self) -> "CameraManager":
        return self

    def __exit__(self, *_: object) -> None:
        self.release()
