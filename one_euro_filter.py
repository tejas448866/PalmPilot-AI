"""Adaptive low-latency One Euro filters."""

import math
from dataclasses import dataclass

from src.hand_tracking.hand_state import Point2D
from src.smoothing.angle_smoothing import angular_delta


def smoothing_factor(cutoff: float, frequency: float) -> float:
    """Return an EMA alpha for the requested cutoff and sample frequency."""
    if cutoff <= 0 or frequency <= 0:
        raise ValueError("cutoff and frequency must be positive")
    tau = 1.0 / (2.0 * math.pi * cutoff)
    period = 1.0 / frequency
    return 1.0 / (1.0 + tau / period)


class OneEuroFilter:
    """Adaptive scalar filter: stable when slow and responsive when fast."""

    def __init__(
        self,
        min_cutoff: float = 1.0,
        beta: float = 0.02,
        derivative_cutoff: float = 1.0,
        frequency: float = 30.0,
    ) -> None:
        if min_cutoff <= 0 or derivative_cutoff <= 0 or frequency <= 0 or beta < 0:
            raise ValueError("invalid One Euro filter parameters")
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.derivative_cutoff = derivative_cutoff
        self.frequency = frequency
        self.value: float | None = None
        self.derivative = 0.0
        self.timestamp: float | None = None

    def update(self, value: float, timestamp: float | None = None) -> float:
        """Filter one value, adapting cutoff from its movement speed."""
        if self.value is None:
            self.value = value
            self.timestamp = timestamp
            return value
        frequency = self.frequency
        if timestamp is not None and self.timestamp is not None:
            elapsed = timestamp - self.timestamp
            if elapsed > 1e-6:
                frequency = 1.0 / elapsed
        raw_derivative = (value - self.value) * frequency
        derivative_alpha = smoothing_factor(self.derivative_cutoff, frequency)
        self.derivative += derivative_alpha * (raw_derivative - self.derivative)
        cutoff = self.min_cutoff + self.beta * abs(self.derivative)
        alpha = smoothing_factor(cutoff, frequency)
        self.value += alpha * (value - self.value)
        self.timestamp = timestamp
        return self.value

    def tune(self, min_cutoff: float, beta: float) -> None:
        """Apply runtime tuning without discarding filter state."""
        if min_cutoff <= 0 or beta < 0:
            raise ValueError("invalid runtime filter tuning")
        self.min_cutoff = min_cutoff
        self.beta = beta

    def reset(self) -> None:
        """Forget filter state."""
        self.value = None
        self.derivative = 0.0
        self.timestamp = None


class OneEuroAngleFilter(OneEuroFilter):
    """One Euro filter that follows the shortest circular angle path."""

    def update(self, value: float, timestamp: float | None = None) -> float:
        """Filter an angle in degrees without wraparound artifacts."""
        if self.value is None:
            return super().update(value, timestamp)
        unwrapped = self.value + angular_delta(value, self.value)
        filtered = super().update(unwrapped, timestamp)
        self.value = (filtered + 180.0) % 360.0 - 180.0
        return self.value


@dataclass
class OneEuroPointFilter:
    """Independent adaptive filters for normalized X and Y coordinates."""

    x: OneEuroFilter
    y: OneEuroFilter

    @classmethod
    def create(
        cls,
        min_cutoff: float = 1.0,
        beta: float = 0.02,
        derivative_cutoff: float = 1.0,
        frequency: float = 30.0,
    ) -> "OneEuroPointFilter":
        """Create an identically tuned two-axis filter."""
        return cls(
            OneEuroFilter(min_cutoff, beta, derivative_cutoff, frequency),
            OneEuroFilter(min_cutoff, beta, derivative_cutoff, frequency),
        )

    def update(self, point: Point2D, timestamp: float | None = None) -> Point2D:
        """Filter both point coordinates."""
        return Point2D(self.x.update(point.x, timestamp), self.y.update(point.y, timestamp))

    def tune(self, min_cutoff: float, beta: float) -> None:
        """Tune both coordinates."""
        self.x.tune(min_cutoff, beta)
        self.y.tune(min_cutoff, beta)
