"""Rolling per-stage performance diagnostics."""

import time
from collections import defaultdict, deque
from dataclasses import dataclass

from .fps_counter import FPSCounter


@dataclass(frozen=True)
class PerformanceSnapshot:
    """Display-ready rolling timing values in milliseconds."""

    fps: float = 0.0
    latency_ms: float = 0.0
    frames: int = 0
    duration_seconds: float = 0.0
    capture_ms: float = 0.0
    inference_ms: float = 0.0
    hand_processing_ms: float = 0.0
    steering_ms: float = 0.0
    render_ms: float = 0.0
    processing_ms: float = 0.0


class PerformanceMonitor:
    """Maintain small rolling averages without per-frame logging."""

    STAGES = ("capture", "inference", "hand_processing", "steering", "render", "total")

    def __init__(self, window: int = 20) -> None:
        if window < 1:
            raise ValueError("performance window must be positive")
        self.started = time.perf_counter()
        self.frames = 0
        self.fps = FPSCounter(window)
        self._values: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=window))

    def update(
        self, frame_started: float, timings_seconds: dict[str, float] | None = None
    ) -> PerformanceSnapshot:
        """Complete one frame and return rolling stage timings."""
        now = time.perf_counter()
        timings = dict(timings_seconds or {})
        timings["total"] = timings.get("total", now - frame_started)
        for stage in self.STAGES:
            self._values[stage].append(max(0.0, timings.get(stage, 0.0)) * 1000.0)
        self.frames += 1
        processing = sum(self.average(stage) for stage in ("hand_processing", "steering"))
        return PerformanceSnapshot(
            fps=self.fps.tick(now),
            latency_ms=self.average("total"),
            frames=self.frames,
            duration_seconds=now - self.started,
            capture_ms=self.average("capture"),
            inference_ms=self.average("inference"),
            hand_processing_ms=self.average("hand_processing"),
            steering_ms=self.average("steering"),
            render_ms=self.average("render"),
            processing_ms=processing,
        )

    def average(self, stage: str) -> float:
        """Return a rolling stage average in milliseconds."""
        values = self._values[stage]
        return sum(values) / len(values) if values else 0.0
