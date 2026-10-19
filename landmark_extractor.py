"""Convert MediaPipe output into application dataclasses."""

import time
from typing import Any

from .hand_state import DetectedHand, HandLandmarks, HandTrackingResult, Point2D


class LandmarkExtractor:
    """Extract normalized and pixel coordinates from MediaPipe results."""

    def extract(
        self, result: Any, width: int, height: int, timestamp: float | None = None
    ) -> HandTrackingResult:
        """Convert a MediaPipe result, safely handling no hands."""
        landmarks = result.multi_hand_landmarks or []
        handedness = result.multi_handedness or []
        hands: list[DetectedHand] = []
        for index, raw_hand in enumerate(landmarks):
            classification = (
                handedness[index].classification[0] if index < len(handedness) else None
            )
            normalized = tuple(Point2D(float(p.x), float(p.y)) for p in raw_hand.landmark)
            pixels = tuple(Point2D(p.x * width, p.y * height) for p in normalized)
            hands.append(
                DetectedHand(
                    handedness=str(classification.label) if classification else "Unknown",
                    score=float(classification.score) if classification else 0.0,
                    landmarks=HandLandmarks(normalized, pixels),
                )
            )
        return HandTrackingResult(
            tuple(hands), time.perf_counter() if timestamp is None else timestamp
        )
