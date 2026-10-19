"""Synchronized rendered video and steering telemetry recording."""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TextIO

from src.gesture import Command
from src.gesture.steering_detector import SteeringResult

from .video_recorder import VideoRecorder


@dataclass(frozen=True)
class SessionPaths:
    """Artifacts produced for one recorded session."""

    directory: Path
    video: Path
    telemetry: Path
    metadata: Path


class SessionRecorder:
    """Record HUD video and newline-delimited synchronized state."""

    def __init__(self, root: Path, codec: str, fps: float) -> None:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.directory = root / f"session_{stamp}"
        self.video = VideoRecorder(self.directory, codec, fps)
        self.telemetry_stream: TextIO | None = None
        self.paths: SessionPaths | None = None

    def start(
        self,
        frame_size: tuple[int, int],
        profile_name: str,
        calibration_path: str | None,
        camera: dict[str, Any],
    ) -> SessionPaths:
        """Open artifacts and write immutable session metadata."""
        self.directory.mkdir(parents=True, exist_ok=True)
        video_path = self.video.start(frame_size)
        telemetry_path = self.directory / "telemetry.jsonl"
        metadata_path = self.directory / "metadata.json"
        metadata_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "profile": profile_name,
                    "calibration": calibration_path,
                    "camera": camera,
                    "video": video_path.name,
                    "telemetry": telemetry_path.name,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        self.telemetry_stream = telemetry_path.open("w", encoding="utf-8")
        self.paths = SessionPaths(self.directory, video_path, telemetry_path, metadata_path)
        return self.paths

    def write(
        self,
        frame: Any,
        timestamp: float,
        steering: SteeringResult,
        pedal: Command,
    ) -> None:
        """Write one rendered frame and matching telemetry record."""
        self.video.write(frame)
        if self.telemetry_stream:
            self.telemetry_stream.write(
                json.dumps(
                    {
                        "timestamp": timestamp,
                        "raw_angle": steering.raw_angle_degrees,
                        "calibrated_angle": steering.calibrated_angle_degrees,
                        "smoothed_angle": steering.smoothed_angle_degrees,
                        "steering_value": steering.normalized_steering_value,
                        "command": steering.command.value,
                        "pedal": pedal.value,
                        "confidence": steering.confidence,
                        "valid": steering.valid,
                        "profile": steering.profile_name,
                    }
                )
                + "\n"
            )

    def stop(self) -> None:
        """Flush and close both video and telemetry."""
        self.video.stop()
        if self.telemetry_stream:
            self.telemetry_stream.flush()
            self.telemetry_stream.close()
            self.telemetry_stream = None
