"""Exponential signal smoothing."""


class ExponentialSmoother:
    """Smooth a numeric stream using an exponential moving average."""

    def __init__(self, alpha: float) -> None:
        if not 0.0 < alpha <= 1.0:
            raise ValueError("alpha must be in (0, 1]")
        self.alpha = alpha
        self.value: float | None = None

    def update(self, sample: float) -> float:
        """Add a sample and return the smoothed value."""
        self.value = (
            sample if self.value is None else self.alpha * sample + (1 - self.alpha) * self.value
        )
        return self.value

    def reset(self) -> None:
        """Forget previous state."""
        self.value = None
