"""Compose role-aware landmarks, wheel geometry, and diagnostics HUD."""

from dataclasses import dataclass
from typing import Any

from src.camera import CameraDiagnostics
from src.gesture import Command
from src.gesture.steering_detector import SteeringResult
from src.hand_tracking import HandTrackingResult, SteeringHands
from src.ml import RecognitionDiagnostics
from src.performance import PerformanceSnapshot

from .landmark_renderer import LandmarkStyle, draw_landmarks
from .status_panel import draw_status
from .steering_renderer import draw_steering


@dataclass(frozen=True)
class VisualizationSettings:
    """Runtime visualization configuration."""

    ui_scale: float = 1.0
    landmark_radius: int = 5
    palm_landmark_radius: int = 7
    connection_thickness: int = 2
    steering_line_thickness: int = 5
    panel_alpha: float = 0.55
    show_camera_diagnostics: bool = True
    show_performance_metrics: bool = True
    show_raw_angle: bool = True
    show_smoothed_angle: bool = True
    show_wheel_circle: bool = True
    show_confidence_bar: bool = True
    show_recommendations: bool = True


def build_hud_lines(
    hands: HandTrackingResult,
    roles: SteeringHands | None,
    steering: SteeringResult,
    pedal: Command,
    performance: PerformanceSnapshot | None,
    camera: CameraDiagnostics | None,
    settings: VisualizationSettings,
    recommendation: str | None = None,
    recognition: RecognitionDiagnostics | None = None,
) -> list[str]:
    """Build HUD text safely even when optional diagnostics are unavailable."""
    live = sum(
        bool(tracked and not tracked.stale)
        for tracked in (
            roles.steering_left if roles else None,
            roles.steering_right if roles else None,
        )
    )
    stale = sum(
        bool(tracked and tracked.stale)
        for tracked in (
            roles.steering_left if roles else None,
            roles.steering_right if roles else None,
        )
    )
    tracking = "LIVE" if steering.valid and not stale else "PREDICTED" if steering.valid else "LOST"
    lines = [
        f"Tracking: {tracking} | detected {len(hands.hands)} | live {live} | stale {stale}",
        f"Steering: {steering.command.value.upper()} | "
        f"value {steering.normalized_steering_value:+.2f} | profile {steering.profile_name}",
        f"Gesture confidence: {steering.confidence:.0%}",
        f"Accelerator: {'ON' if pedal is Command.ACCELERATE else 'off'} | "
        f"Brake: {'ON' if pedal in (Command.BRAKE, Command.REVERSE) else 'off'}",
    ]
    if recognition:
        loaded = "yes" if recognition.model_loaded else "no"
        fingers = "/".join(
            f"{name[0].upper()}:{state[0].upper()}"
            for name, state in zip(
                ("thumb", "index", "middle", "ring", "pinky"),
                recognition.finger_states,
                strict=False,
            )
        )
        lines.extend(
            [
                f"Recognition: {recognition.mode} | model loaded: {loaded} | "
                f"hand: {'yes' if recognition.hand_detected else 'no'}",
                f"Fingers: {fingers or 'n/a'} | openness {recognition.openness_score:.2f}",
                f"Deterministic: {recognition.deterministic_gesture} | "
                f"ML: {recognition.ml_gesture}",
                f"ML raw/stable: {recognition.raw_label} / {recognition.stable_label} | "
                f"confidence {recognition.confidence:.0%}",
                f"Final: {recognition.final_gesture} | stability "
                f"{recognition.stability_frames} | action {recognition.mapped_action}",
            ]
        )
        if recognition.rejection_reason:
            lines.append(f"ML rejection: {recognition.rejection_reason}")
    if settings.show_raw_angle:
        raw = "n/a" if steering.raw_angle_degrees is None else f"{steering.raw_angle_degrees:+.1f}°"
        calibrated = (
            "n/a"
            if steering.calibrated_angle_degrees is None
            else f"{steering.calibrated_angle_degrees:+.1f}°"
        )
        lines.append(f"Angle raw/calibrated: {raw} / {calibrated}")
    if settings.show_smoothed_angle:
        lines.append(f"Angle smoothed: {steering.smoothed_angle_degrees:+.1f}°")
    if settings.show_camera_diagnostics:
        if camera:
            processing = camera.processing_resolution or camera.actual_resolution
            lines.append(
                f"Camera: {camera.backend} {camera.actual_resolution[0]}x"
                f"{camera.actual_resolution[1]} | process {processing[0]}x{processing[1]}"
            )
        else:
            lines.append("Camera diagnostics: unavailable")
    if settings.show_performance_metrics:
        metrics = performance or PerformanceSnapshot()
        lines.extend(
            [
                f"FPS {metrics.fps:.1f} | total {metrics.latency_ms:.1f} ms | "
                f"capture {metrics.capture_ms:.1f} ms",
                f"inference {metrics.inference_ms:.1f} | hand {metrics.hand_processing_ms:.1f} | "
                f"steer {metrics.steering_ms:.1f} | render {metrics.render_ms:.1f} ms",
            ]
        )
    lines.append("Q / Esc: safely exit")
    if settings.show_recommendations and recommendation:
        lines.insert(-1, f"Recommendation: {recommendation}")
    return lines


class OverlayRenderer:
    """Render the same tracking and steering state used for keyboard control."""

    def __init__(
        self,
        draw_landmark_points: bool = True,
        draw_status_panel: bool = True,
        settings: VisualizationSettings | None = None,
    ) -> None:
        self.draw_landmark_points = draw_landmark_points
        self.draw_status_panel = draw_status_panel
        self.settings = settings or VisualizationSettings()
        self.landmark_style = LandmarkStyle(
            self.settings.landmark_radius,
            self.settings.palm_landmark_radius,
            self.settings.connection_thickness,
            self.settings.ui_scale,
        )

    def render(
        self,
        frame: Any,
        hands: HandTrackingResult,
        steering: SteeringResult,
        pedal: Command,
        performance: PerformanceSnapshot | None,
        active_keys: set[str],
        dry_run: bool,
        recording: bool,
        calibrated: bool,
        roles: SteeringHands | None = None,
        camera: CameraDiagnostics | None = None,
        recommendation: str | None = None,
        recognition: RecognitionDiagnostics | None = None,
    ) -> Any:
        """Annotate the full-resolution frame without recalculating commands."""
        del active_keys, recording, calibrated
        if self.draw_landmark_points:
            draw_landmarks(frame, hands, roles, self.landmark_style)
        draw_steering(
            frame,
            steering,
            roles,
            self.settings.steering_line_thickness,
            self.settings.ui_scale,
            self.settings.show_wheel_circle,
        )
        if self.draw_status_panel:
            draw_status(
                frame,
                build_hud_lines(
                    hands,
                    roles,
                    steering,
                    pedal,
                    performance,
                    camera,
                    self.settings,
                    recommendation,
                    recognition,
                ),
                dry_run,
                self.settings.panel_alpha,
                self.settings.ui_scale,
            )
        if self.settings.show_confidence_bar:
            self._draw_confidence(frame, steering.confidence)
        return frame

    def _draw_confidence(self, frame: Any, confidence: float) -> None:
        """Draw a compact confidence bar without allocating another overlay."""
        import cv2

        height, width = frame.shape[:2]
        scale = max(0.65, height / 720.0) * self.settings.ui_scale
        bar_width = round(220 * scale)
        bar_height = round(12 * scale)
        x, y = width - bar_width - round(24 * scale), round(28 * scale)
        cv2.rectangle(
            frame,
            (x, y),
            (x + bar_width, y + bar_height),
            (35, 40, 48),
            -1,
            cv2.LINE_AA,
        )
        color = (70, 220, 100) if confidence >= 0.7 else (60, 180, 255)
        cv2.rectangle(
            frame,
            (x, y),
            (x + round(bar_width * max(0.0, min(1.0, confidence))), y + bar_height),
            color,
            -1,
            cv2.LINE_AA,
        )
