"""Factories for synthetic hand landmarks."""

from src.hand_tracking import DetectedHand, HandLandmarks, HandTrackingResult, Point2D


def make_hand(label: str, x: float, y: float) -> DetectedHand:
    """Build a 21-point synthetic hand centered on one point."""
    normalized = tuple(Point2D(x, y) for _ in range(21))
    pixels = tuple(Point2D(x * 100, y * 100) for _ in range(21))
    return DetectedHand(label, 0.99, HandLandmarks(normalized, pixels))


def make_two_hands(left_y: float = 0.5, right_y: float = 0.5) -> HandTrackingResult:
    """Build a classified two-hand result."""
    return HandTrackingResult(
        (
            make_hand("Left", 0.3, left_y),
            make_hand("Right", 0.7, right_y),
        )
    )
