"""Structured hand-tracking state."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Point2D:
    """A normalized or pixel-space 2D point."""

    x: float
    y: float


@dataclass(frozen=True)
class HandLandmarks:
    """Normalized and pixel landmark sets."""

    normalized: tuple[Point2D, ...]
    pixels: tuple[Point2D, ...]

    def point(self, index: int, pixel: bool = False) -> Point2D:
        """Retrieve a landmark by centralized numeric index."""
        return (self.pixels if pixel else self.normalized)[index]


@dataclass(frozen=True)
class DetectedHand:
    """One detected hand and classification metadata."""

    handedness: str
    score: float
    landmarks: HandLandmarks
    visible: bool = True


@dataclass(frozen=True)
class HandTrackingResult:
    """All hands detected in one frame."""

    hands: tuple[DetectedHand, ...] = field(default_factory=tuple)
    timestamp: float = 0.0

    def by_handedness(self, label: str) -> DetectedHand | None:
        """Find the strongest matching hand."""
        matches = [hand for hand in self.hands if hand.handedness.lower() == label.lower()]
        return max(matches, key=lambda hand: hand.score, default=None)
