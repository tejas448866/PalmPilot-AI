"""Moving-average signal smoother."""

from collections import deque


class MovingAverage:
    """Maintain a fixed-size numeric moving average."""

    def __init__(self, window_size: int) -> None:
        if window_size < 1:
            raise ValueError("window_size must be positive")
        self.values: deque[float] = deque(maxlen=window_size)

    def update(self, value: float) -> float:
        """Add one sample and return the current average."""
        self.values.append(value)
        return sum(self.values) / len(self.values)

    def reset(self) -> None:
        """Forget all samples."""
        self.values.clear()
