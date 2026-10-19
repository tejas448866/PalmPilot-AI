"""Controllable recorded-session replay."""

import json
from pathlib import Path
from typing import Any

from src.exceptions import RecordingError


class ReplayController:
    """Pause, step, seek, and speed-control a recorded HUD video."""

    def __init__(self, session_directory: Path) -> None:
        import cv2

        metadata_path = session_directory / "metadata.json"
        if not metadata_path.exists():
            raise RecordingError(f"Missing replay metadata: {metadata_path}")
        self.metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        self.capture = cv2.VideoCapture(str(session_directory / self.metadata["video"]))
        if not self.capture.isOpened():
            raise RecordingError("Recorded session video could not be opened")
        self.fps = float(self.capture.get(cv2.CAP_PROP_FPS) or 30.0)
        self.frame_count = int(self.capture.get(getattr(cv2, "CAP_PROP_FRAME_COUNT", 7)))
        self.speed = 1.0
        self.paused = False

    def read(self) -> tuple[bool, Any]:
        """Read one frame unless paused."""
        if self.paused:
            return False, None
        return self.capture.read()

    def step(self, frames: int = 1) -> tuple[bool, Any]:
        """Move an exact number of frames and return the destination."""
        import cv2

        current = int(self.capture.get(cv2.CAP_PROP_POS_FRAMES))
        self.capture.set(cv2.CAP_PROP_POS_FRAMES, max(0, current + frames - 1))
        return self.capture.read()

    def seek_frame(self, frame: int) -> None:
        """Jump to an absolute frame."""
        import cv2

        self.capture.set(cv2.CAP_PROP_POS_FRAMES, max(0, min(frame, self.frame_count - 1)))

    def seek_timestamp(self, seconds: float) -> None:
        """Jump to a session-relative timestamp."""
        self.seek_frame(round(max(0.0, seconds) * self.fps))

    def set_speed(self, speed: float) -> None:
        """Set replay speed in the supported 0.1x–4x range."""
        if not 0.1 <= speed <= 4.0:
            raise ValueError("replay speed must be between 0.1 and 4.0")
        self.speed = speed

    @property
    def delay_ms(self) -> int:
        """OpenCV wait delay for current speed."""
        return max(1, round(1000.0 / (self.fps * self.speed)))

    def close(self) -> None:
        """Release replay resources."""
        self.capture.release()


def replay_session(session_directory: Path) -> int:
    """Play a session with keyboard pause, stepping, seeking, and speed control."""
    import cv2

    replay = ReplayController(session_directory)
    try:
        last_frame: Any | None = None
        while True:
            if not replay.paused:
                success, frame = replay.read()
                if not success:
                    return 0
                last_frame = frame
            if last_frame is not None:
                cv2.imshow("Session replay", last_frame)
            key = cv2.waitKey(replay.delay_ms) & 0xFF
            if key in (ord("q"), ord("Q"), 27):
                return 0
            if key == ord(" "):
                replay.paused = not replay.paused
            elif key in (ord("."), 83):
                replay.paused = True
                success, frame = replay.step(1)
                if success:
                    last_frame = frame
            elif key in (ord(","), 81):
                replay.paused = True
                success, frame = replay.step(-1)
                if success:
                    last_frame = frame
            elif key == ord("+"):
                replay.set_speed(min(4.0, replay.speed * 1.25))
            elif key == ord("-"):
                replay.set_speed(max(0.1, replay.speed / 1.25))
    finally:
        replay.close()
        cv2.destroyAllWindows()
