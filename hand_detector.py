"""MediaPipe Hands adapter."""

from typing import Any

from src.exceptions import HandTrackingError


class HandDetector:
    """Own and execute a MediaPipe Hands graph."""

    def __init__(
        self,
        max_num_hands: int = 2,
        min_detection_confidence: float = 0.55,
        min_tracking_confidence: float = 0.50,
        model_complexity: int = 1,
        static_image_mode: bool = False,
    ) -> None:
        try:
            import mediapipe as mp

            self._hands = mp.solutions.hands.Hands(
                static_image_mode=static_image_mode,
                max_num_hands=max_num_hands,
                min_detection_confidence=min_detection_confidence,
                min_tracking_confidence=min_tracking_confidence,
                model_complexity=model_complexity,
            )
        except (ImportError, AttributeError) as exc:
            raise HandTrackingError(
                "MediaPipe Hands is unavailable. Install requirements for Python 3.10/3.11."
            ) from exc

    def process(self, rgb_frame: Any) -> Any:
        """Detect hands in an RGB frame."""
        return self._hands.process(rgb_frame)

    def close(self) -> None:
        """Release MediaPipe resources."""
        self._hands.close()
