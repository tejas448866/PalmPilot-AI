"""Rolling latency statistics."""

from collections import deque


class LatencyTracker:
    """Track current and rolling-average milliseconds."""

    def __init__(self, window: int = 30) -> None:
        self.values: deque[float] = deque(maxlen=window)

    def add_seconds(self, seconds: float) -> float:
        """Add seconds and return average milliseconds."""
        self.values.append(seconds * 1000.0)
        return self.average_ms

    @property
    def average_ms(self) -> float:
        """Return the rolling mean."""
        return sum(self.values) / len(self.values) if self.values else 0.0
