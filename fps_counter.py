"""Rolling FPS calculation."""

import time
from collections import deque


class FPSCounter:
    """Estimate FPS over a rolling timestamp window."""

    def __init__(self, window: int = 30) -> None:
        self.timestamps: deque[float] = deque(maxlen=max(2, window))

    def tick(self, now: float | None = None) -> float:
        """Record a frame and return rolling FPS."""
        self.timestamps.append(now if now is not None else time.perf_counter())
        if len(self.timestamps) < 2:
            return 0.0
        elapsed = self.timestamps[-1] - self.timestamps[0]
        return (len(self.timestamps) - 1) / elapsed if elapsed > 0 else 0.0
