"""Safe OpenCV-frame presentation inside Qt."""

from typing import Any


def aspect_fit_size(
    source_width: int,
    source_height: int,
    available_width: int,
    available_height: int,
) -> tuple[int, int]:
    """Fit one rectangle inside another without stretching or cropping."""
    if min(source_width, source_height, available_width, available_height) <= 0:
        return 0, 0
    scale = min(available_width / source_width, available_height / source_height)
    return max(1, round(source_width * scale)), max(1, round(source_height * scale))


def bgr_frame_to_qimage(frame: Any) -> Any:
    """Convert BGR NumPy storage into an owning RGB QImage."""
    import cv2
    from PySide6.QtGui import QImage

    if frame is None or not getattr(frame, "size", 0):
        raise ValueError("Cannot display an empty camera frame")
    if getattr(frame, "ndim", 0) != 3 or frame.shape[2] != 3:
        raise ValueError("Camera preview requires a three-channel BGR image")
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    height, width = rgb.shape[:2]
    image = QImage(
        rgb.data,
        width,
        height,
        int(rgb.strides[0]),
        QImage.Format.Format_RGB888,
    )
    return image.copy()


def create_camera_preview_class() -> type:
    """Create the QLabel subclass lazily so CLI imports do not require Qt."""
    from PySide6.QtCore import QSize, Qt
    from PySide6.QtGui import QImage, QPixmap
    from PySide6.QtWidgets import QLabel, QSizePolicy

    class CameraPreview(QLabel):
        """Aspect-preserving, smoothly scaled integrated camera surface."""

        def __init__(self) -> None:
            super().__init__("Start Controller Test or LIVE mode to begin camera preview")
            self._image = QImage()
            self.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setMinimumSize(320, 180)
            policy = QSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Preferred,
            )
            policy.setHeightForWidth(True)
            self.setSizePolicy(policy)
            self.setObjectName("cameraPreview")
            self.mode_badge = QLabel("STOPPED", self)
            self.mode_badge.setObjectName("previewModeBadge")
            self.mode_badge.adjustSize()

        def hasHeightForWidth(self) -> bool:
            return True

        def heightForWidth(self, width: int) -> int:
            return round(width * 9 / 16)

        def sizeHint(self) -> QSize:
            return QSize(640, 360)

        def set_mode(self, mode: str) -> None:
            """Show a short safety state without obscuring the video."""
            normalized = mode.upper()
            if normalized == "TEST":
                text = "TEST · NO KEY OUTPUT"
            elif normalized == "LIVE":
                text = "LIVE · KEYS ENABLED"
            else:
                text = normalized
            self.mode_badge.setText(text)
            self.mode_badge.adjustSize()

        def set_frame(self, frame: Any) -> None:
            """Take ownership of a rendered frame and display it."""
            self._image = bgr_frame_to_qimage(frame)
            self._refresh()

        def clear_frame(self, message: str = "Camera stopped") -> None:
            """Clear stale imagery and display an honest state message."""
            self._image = QImage()
            self.clear()
            self.setText(message)

        def resizeEvent(self, event: Any) -> None:
            super().resizeEvent(event)
            self.mode_badge.move(10, 10)
            self.mode_badge.raise_()
            self._refresh()

        def _refresh(self) -> None:
            if self._image.isNull():
                return
            pixmap = QPixmap.fromImage(self._image).scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.setPixmap(pixmap)

    return CameraPreview
