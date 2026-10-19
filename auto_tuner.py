"""Lightweight camera quality analysis and recommendations."""

from dataclasses import dataclass
from typing import Any

from .camera_manager import CameraDiagnostics


@dataclass(frozen=True)
class CameraRecommendation:
    """Current lighting rating and actionable camera recommendation."""

    lighting_quality: str
    brightness: float
    message: str


def analyze_camera(
    frame: Any,
    diagnostics: CameraDiagnostics,
    fps: float,
    latency_ms: float,
) -> CameraRecommendation:
    """Recommend settings from actual mode, throughput, and mean brightness."""
    brightness = float(frame.mean()) if hasattr(frame, "mean") else 128.0
    lighting = "dark" if brightness < 55 else "bright" if brightness > 220 else "good"
    recommendations: list[str] = []
    if lighting == "dark":
        recommendations.append("add front lighting")
    elif lighting == "bright":
        recommendations.append("reduce glare/exposure")
    processing = diagnostics.processing_resolution or diagnostics.actual_resolution
    if fps < 24 or latency_ms > 40:
        target = 480 if processing[0] > 480 else processing[0]
        recommendations.append(f"try processing_width={target}")
    if diagnostics.backend == "default":
        recommendations.append("compare dshow and msmf")
    if diagnostics.actual_resolution != diagnostics.requested_resolution:
        recommendations.append("camera rejected requested resolution")
    return CameraRecommendation(
        lighting, brightness, "; ".join(recommendations) or "camera settings look balanced"
    )
