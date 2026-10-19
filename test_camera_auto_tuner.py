"""Camera recommendation logic."""

from src.camera import CameraDiagnostics
from src.camera.auto_tuner import analyze_camera


class DarkFrame:
    """Array-like frame brightness fixture."""

    @staticmethod
    def mean() -> float:
        return 30.0


def test_dark_slow_camera_gets_actionable_recommendations() -> None:
    diagnostics = CameraDiagnostics(
        0, "default", (1280, 720), (640, 480), (640, 480), (640, 480), (640, 480)
    )
    result = analyze_camera(DarkFrame(), diagnostics, fps=18, latency_ms=60)
    assert result.lighting_quality == "dark"
    assert "front lighting" in result.message
    assert "processing_width" in result.message
