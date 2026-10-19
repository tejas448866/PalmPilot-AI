"""Time- and pose-diversity-aware dataset sample acceptance."""

import math
from dataclasses import dataclass
from enum import Enum


class CaptureState(str, Enum):
    """Reason a detected pose is ready or temporarily rejected."""

    READY = "ready"
    WAITING = "waiting"
    TOO_SIMILAR = "too_similar"


@dataclass(frozen=True)
class CaptureDecision:
    """One side-effect-free capture decision."""

    state: CaptureState
    seconds_remaining: float = 0.0
    feature_distance: float | None = None

    @property
    def ready(self) -> bool:
        """Whether the caller may persist this feature vector."""
        return self.state is CaptureState.READY


class DatasetCapturePolicy:
    """Pace accepted samples and require meaningful feature variation."""

    def __init__(
        self,
        capture_interval_seconds: float = 0.9,
        minimum_feature_distance: float = 0.015,
    ) -> None:
        if capture_interval_seconds < 0.1:
            raise ValueError("capture_interval_seconds must be at least 0.1")
        if minimum_feature_distance < 0:
            raise ValueError("minimum_feature_distance cannot be negative")
        self.capture_interval_seconds = capture_interval_seconds
        self.minimum_feature_distance = minimum_feature_distance
        self.last_accepted_at: float | None = None
        self.last_features: tuple[float, ...] | None = None

    @staticmethod
    def feature_distance(first: tuple[float, ...], second: tuple[float, ...]) -> float:
        """Return root-mean-square distance across normalized features."""
        if not first or len(first) != len(second):
            raise ValueError("Feature vectors must have the same non-zero length")
        squared = sum((left - right) ** 2 for left, right in zip(first, second, strict=True))
        distance = math.sqrt(squared / len(first))
        if not math.isfinite(distance):
            raise ValueError("Feature distance must be finite")
        return distance

    def evaluate(self, features: tuple[float, ...], now: float) -> CaptureDecision:
        """Check pacing and diversity without changing acceptance state."""
        if self.last_accepted_at is not None:
            elapsed = now - self.last_accepted_at
            remaining = self.capture_interval_seconds - elapsed
            if remaining > 0:
                return CaptureDecision(CaptureState.WAITING, remaining)
        distance = (
            self.feature_distance(self.last_features, features)
            if self.last_features is not None
            else None
        )
        if distance is not None and distance < self.minimum_feature_distance:
            return CaptureDecision(CaptureState.TOO_SIMILAR, feature_distance=distance)
        return CaptureDecision(CaptureState.READY, feature_distance=distance)

    def mark_accepted(self, features: tuple[float, ...], now: float) -> None:
        """Start the interval only after durable dataset acceptance."""
        self.last_features = features
        self.last_accepted_at = now
