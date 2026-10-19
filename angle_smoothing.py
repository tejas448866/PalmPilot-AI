"""Low-latency circular angle smoothing with median spike filtering."""

import statistics
from collections import deque


def angular_delta(target: float, source: float) -> float:
    """Return shortest signed difference in degrees."""
    return (target - source + 180.0) % 360.0 - 180.0


class AngleSmoother:
    """Median-filter then circular-EMA an angle stream."""

    def __init__(self, alpha: float = 0.35, median_window: int = 3) -> None:
        if not 0 < alpha <= 1:
            raise ValueError("alpha must be in (0, 1]")
        if median_window < 1:
            raise ValueError("median_window must be positive")
        self.alpha = alpha
        self.samples: deque[float] = deque(maxlen=median_window)
        self.value: float | None = None

    def update(self, angle: float) -> float:
        """Add an angle and return a wrap-safe smoothed value."""
        self.samples.append(angle)
        if self.value is None:
            filtered = float(statistics.median(self.samples))
            self.value = filtered
            return filtered
        unwrapped = [self.value + angular_delta(sample, self.value) for sample in self.samples]
        filtered = float(statistics.median(unwrapped))
        self.value = (
            self.value + self.alpha * angular_delta(filtered, self.value) + 180
        ) % 360 - 180
        return self.value

    def reset(self) -> None:
        """Forget all samples."""
        self.samples.clear()
        self.value = None
