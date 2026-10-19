"""Constant-memory end-of-session diagnostic aggregation."""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class SessionStatistics:
    """Streaming FPS, confidence, loss, and steering-variance metrics."""

    frame_count: int = 0
    fps_count: int = 0
    fps_sum: float = 0.0
    minimum_fps: float = float("inf")
    confidence_sum: float = 0.0
    steering_mean: float = 0.0
    steering_m2: float = 0.0
    tracking_loss_count: int = 0
    previous_tracking_valid: bool = True
    tracking_recovered_at: float | None = None
    reaction_time_sum: float = 0.0
    reaction_count: int = 0
    profile_usage: dict[str, int] = field(default_factory=dict)
    steering_histogram: list[int] = field(default_factory=lambda: [0] * 10)

    @classmethod
    def create(cls) -> "SessionStatistics":
        """Create empty statistics."""
        return cls()

    def update(
        self,
        fps: float,
        confidence: float,
        steering_value: float,
        tracking_valid: bool,
        timestamp: float | None = None,
        profile: str = "unknown",
    ) -> None:
        """Update all metrics in constant memory."""
        self.frame_count += 1
        if fps > 0:
            self.fps_count += 1
            self.fps_sum += fps
            self.minimum_fps = min(self.minimum_fps, fps)
        self.confidence_sum += confidence
        delta = steering_value - self.steering_mean
        self.steering_mean += delta / self.frame_count
        self.steering_m2 += delta * (steering_value - self.steering_mean)
        self.profile_usage[profile] = self.profile_usage.get(profile, 0) + 1
        bin_index = min(9, max(0, int((steering_value + 1.0) * 5)))
        self.steering_histogram[bin_index] += 1
        if self.previous_tracking_valid and not tracking_valid:
            self.tracking_loss_count += 1
            self.tracking_recovered_at = None
        elif not self.previous_tracking_valid and tracking_valid:
            self.tracking_recovered_at = timestamp
        if (
            self.tracking_recovered_at is not None
            and timestamp is not None
            and abs(steering_value) > 0.05
        ):
            self.reaction_time_sum += max(0.0, timestamp - self.tracking_recovered_at)
            self.reaction_count += 1
            self.tracking_recovered_at = None
        self.previous_tracking_valid = tracking_valid

    def report(
        self, runtime_seconds: float, camera: dict[str, Any], profile: str
    ) -> dict[str, Any]:
        """Build a JSON-serializable summary."""
        return {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "runtime_seconds": runtime_seconds,
            "average_fps": self.fps_sum / self.fps_count if self.fps_count else 0.0,
            "minimum_fps": self.minimum_fps if self.fps_count else 0.0,
            "tracking_loss_count": self.tracking_loss_count,
            "average_confidence": (
                self.confidence_sum / self.frame_count if self.frame_count else 0.0
            ),
            "steering_variance": (
                self.steering_m2 / self.frame_count if self.frame_count > 1 else 0.0
            ),
            "profile": profile,
            "profile_usage_frames": dict(self.profile_usage),
            "average_reaction_time_seconds": (
                self.reaction_time_sum / self.reaction_count if self.reaction_count else 0.0
            ),
            "steering_histogram": list(self.steering_histogram),
            "camera": camera,
        }

    def save(
        self,
        directory: Path,
        runtime_seconds: float,
        camera: dict[str, Any],
        profile: str,
    ) -> Path:
        """Write a timestamped JSON report."""
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"session_{datetime.now():%Y%m%d_%H%M%S}.json"
        path.write_text(
            json.dumps(self.report(runtime_seconds, camera, profile), indent=2),
            encoding="utf-8",
        )
        return path
