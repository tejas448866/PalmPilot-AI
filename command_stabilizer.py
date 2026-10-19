"""Frame-count command debounce."""

from typing import Generic, TypeVar

T = TypeVar("T")


class CommandStabilizer(Generic[T]):
    """Commit a new command only after consecutive observations."""

    def __init__(self, stable_frames: int, initial: T) -> None:
        if stable_frames < 1:
            raise ValueError("stable_frames must be positive")
        self.stable_frames = stable_frames
        self.current = initial
        self.candidate = initial
        self.count = 0

    def update(self, value: T) -> T:
        """Observe a value and return the committed command."""
        if value == self.current:
            self.candidate, self.count = value, 0
        elif value != self.candidate:
            self.candidate, self.count = value, 1
        else:
            self.count += 1
        if self.count >= self.stable_frames:
            self.current, self.count = self.candidate, 0
        return self.current
