"""Webcam-assisted Version 2 controller calibration."""

import argparse
import statistics
from collections.abc import Callable
from pathlib import Path
from typing import Any

try:
    from scripts import _bootstrap  # noqa: F401
except ModuleNotFoundError:
    import _bootstrap  # type: ignore[no-redef]  # noqa: F401

from src.calibration import (
    Calibration,
    derive_pedal_thresholds,
    derive_steering,
    save_calibration,
)
from src.camera import CameraManager, FrameProcessor, scale_preview
from src.controller import KeyboardController
from src.exceptions import ApplicationError, CameraError
from src.gesture import Command
from src.gesture.steering_detector import SteeringDetector
from src.hand_tracking.hand_detector import HandDetector
from src.hand_tracking.landmark_extractor import LandmarkExtractor
from src.hand_tracking.role_tracker import HandRoleTracker, SteeringHands
from src.performance import PerformanceSnapshot
from src.utils.file_handler import load_yaml
from src.utils.validators import validate_config
from src.visualization import OverlayRenderer, VisualizationSettings


class CalibrationCancelled(Exception):
    """Normal user cancellation without an error traceback."""


def ask_float(prompt: str, default: float) -> float:
    """Read a float with a displayed default."""
    response = input(f"{prompt} [{default}]: ").strip()
    return float(response) if response else default


def manual_calibration(config: dict[str, Any]) -> Calibration:
    """Collect explicit values and validate them without silently using defaults."""
    print("Manual mode requires measured raw angles from the dry-run HUD.")
    neutral = ask_float("Neutral raw wheel angle", 0.0)
    left = ask_float("Comfortable left raw angle", -45.0)
    right = ask_float("Comfortable right raw angle", 45.0)
    accelerate = ask_float("Both-hand acceleration Y position", 0.30)
    brake = ask_float("Both-hand brake Y position", 0.75)
    invert = input("Invert steering? [y/N]: ").strip().lower() == "y"
    count = int(config["calibration"]["samples_per_stage"])
    derived = derive_steering([neutral] * count, [left] * count, [right] * count, invert, count)
    accelerate_y, brake_y = derive_pedal_thresholds([accelerate] * count, [brake] * count, count)
    tracking = config["hand_tracking"]
    camera = config["camera"]
    return Calibration(
        camera_index=int(camera["index"]),
        requested_resolution=(
            int(camera["requested_width"]),
            int(camera["requested_height"]),
        ),
        preview_flip_horizontal=bool(camera["flip_horizontal"]),
        neutral_angle=derived.neutral_angle,
        maximum_left_angle=derived.calibrated_left_angle,
        maximum_right_angle=derived.calibrated_right_angle,
        dead_zone=derived.dead_zone,
        enter_left_threshold=derived.enter_left_threshold,
        exit_left_threshold=derived.exit_left_threshold,
        enter_right_threshold=derived.enter_right_threshold,
        exit_right_threshold=derived.exit_right_threshold,
        normalized_left_range=derived.normalized_left_range,
        normalized_right_range=derived.normalized_right_range,
        accelerate_y=accelerate_y,
        brake_y=brake_y,
        invert=invert,
        reference_point=str(tracking["reference_point"]),
        persistence_frames=int(tracking["persistence_frames"]),
        persistence_ms=float(tracking["persistence_ms"]),
        point_smoothing_alpha=float(tracking["point_smoothing_alpha"]),
    )


class WebcamCalibrationSession:
    """Own shared Part 1 vision components for staged calibration."""

    def __init__(self, config: dict[str, Any], camera_index: int | None = None) -> None:
        self.config = config
        camera_cfg, tracking_cfg = config["camera"], config["hand_tracking"]
        index = int(camera_cfg["index"] if camera_index is None else camera_index)
        self.keyboard = KeyboardController(dry_run=True)
        self.camera = CameraManager(
            index,
            int(camera_cfg["requested_width"]),
            int(camera_cfg["requested_height"]),
            int(camera_cfg["fps"]),
            list(camera_cfg["backend_order"]),
            list(camera_cfg["fallback_resolutions"]),
            int(camera_cfg["processing_width"]),
            float(camera_cfg["preview_scale"]),
            int(camera_cfg["warmup_frames"]),
            camera_cfg.get("autofocus"),
            camera_cfg.get("exposure"),
        )
        try:
            self.processor = FrameProcessor(
                bool(camera_cfg["flip_horizontal"]),
                self.camera.diagnostics.processing_resolution,
            )
            self.detector = HandDetector(
                **{
                    key: tracking_cfg[key]
                    for key in (
                        "static_image_mode",
                        "max_num_hands",
                        "model_complexity",
                        "min_detection_confidence",
                        "min_tracking_confidence",
                    )
                }
            )
        except Exception:
            self.keyboard.release_all()
            self.camera.release()
            try:
                import cv2

                cv2.destroyAllWindows()
            except ImportError:
                pass
            raise
        self.extractor = LandmarkExtractor()
        self.roles = HandRoleTracker(
            **{
                key: tracking_cfg[key]
                for key in (
                    "reference_point",
                    "persistence_frames",
                    "persistence_ms",
                    "max_reference_jump",
                    "point_smoothing_alpha",
                    "one_euro_enabled",
                    "one_euro_min_cutoff",
                    "one_euro_beta",
                    "one_euro_derivative_cutoff",
                )
            }
            | {"nominal_frequency": float(camera_cfg["fps"])}
        )
        steering_cfg = config["steering"]
        self.steering = SteeringDetector(
            **{
                key: steering_cfg[key]
                for key in (
                    "neutral_angle",
                    "minimum_hand_span",
                    "enter_left_threshold",
                    "exit_left_threshold",
                    "enter_right_threshold",
                    "exit_right_threshold",
                    "maximum_angle",
                    "normalized_left_range",
                    "normalized_right_range",
                    "invert",
                    "angle_smoothing_alpha",
                    "median_window",
                    "max_angle_jump",
                    "one_euro_enabled",
                    "one_euro_min_cutoff",
                    "one_euro_beta",
                    "one_euro_derivative_cutoff",
                    "response_curve",
                    "curve_strength",
                )
            }
            | {
                "nominal_frequency": float(camera_cfg["fps"]),
                "minimum_confidence": float(tracking_cfg["minimum_gesture_confidence"]),
            }
        )
        visual = config["visualization"]
        self.renderer = OverlayRenderer(
            True,
            False,
            VisualizationSettings(
                ui_scale=float(visual["ui_scale"]),
                landmark_radius=int(visual["landmark_radius"]),
                palm_landmark_radius=int(visual["palm_landmark_radius"]),
                connection_thickness=int(visual["connection_thickness"]),
                steering_line_thickness=int(visual["steering_line_thickness"]),
            ),
        )
        self.window = "Controller calibration"

    def next_state(self) -> tuple[Any, Any, SteeringHands, Any]:
        """Capture one full frame and calculate shared tracking/steering state."""
        frame = self.processor.process(self.camera.read())
        raw = self.detector.process(frame.rgb)
        height, width = frame.bgr.shape[:2]
        hands = self.extractor.extract(raw, width, height, frame.timestamp)
        roles = self.roles.update(hands)
        steering = self.steering.detect(roles)
        return frame, hands, roles, steering

    def collect_stage(
        self,
        title: str,
        instruction: str,
        measure: Callable[[Any, SteeringHands], float | None],
        tolerance: float,
    ) -> list[float]:
        """Collect stable valid values with visible progress and retry controls."""
        import cv2

        required = int(self.config["calibration"]["samples_per_stage"])
        window_size = int(self.config["calibration"]["stability_window"])
        samples: list[float] = []
        recent: list[float] = []
        collecting = False
        while len(samples) < required:
            frame, hands, roles, steering = self.next_state()
            measured = measure(steering, roles)
            if collecting and measured is not None and steering.valid:
                recent.append(measured)
                recent = recent[-window_size:]
                if len(recent) == window_size and max(recent) - min(recent) <= tolerance:
                    samples.append(measured)
            rendered = self.renderer.render(
                frame.bgr,
                hands,
                steering,
                Command.IDLE,
                PerformanceSnapshot(),
                set(),
                True,
                False,
                False,
                roles,
                self.camera.diagnostics,
            )
            value_text = "invalid" if measured is None else f"{measured:+.3f}"
            self._instructions(
                rendered,
                title,
                instruction,
                f"Value {value_text} | stable samples {len(samples)}/{required}",
                "SPACE start/pause | R retry | Q/Esc cancel",
            )
            cv2.imshow(
                self.window,
                scale_preview(rendered, float(self.config["camera"]["preview_scale"])),
            )
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("Q"), 27):
                raise CalibrationCancelled()
            if key in (ord("r"), ord("R")):
                samples.clear()
                recent.clear()
                collecting = False
            elif key == ord(" "):
                collecting = not collecting
        return samples

    def review(self, lines: list[str]) -> None:
        """Display derived values and require explicit save confirmation."""
        import cv2

        while True:
            frame, hands, roles, steering = self.next_state()
            rendered = self.renderer.render(
                frame.bgr,
                hands,
                steering,
                Command.IDLE,
                None,
                set(),
                True,
                False,
                False,
                roles,
                self.camera.diagnostics,
            )
            self._instructions(
                rendered,
                "Review calibration",
                " | ".join(lines[:2]),
                " | ".join(lines[2:]),
                "S save | Q/Esc cancel",
            )
            cv2.imshow(self.window, rendered)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("Q"), 27):
                raise CalibrationCancelled()
            if key in (ord("s"), ord("S")):
                return

    @staticmethod
    def _instructions(frame: Any, *lines: str) -> None:
        import cv2

        height, width = frame.shape[:2]
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, height - 145), (width, height), (10, 15, 20), -1)
        cv2.addWeighted(overlay, 0.72, frame, 0.28, 0, frame)
        for index, line in enumerate(lines):
            cv2.putText(
                frame,
                line,
                (24, height - 110 + index * 29),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.66,
                (240, 245, 250),
                2 if index == 0 else 1,
                cv2.LINE_AA,
            )

    def close(self) -> None:
        """Release every owned hardware/input/GUI resource."""
        import cv2

        self.keyboard.release_all()
        self.detector.close()
        self.camera.release()
        cv2.destroyAllWindows()


def webcam_calibration(
    config: dict[str, Any], camera_index: int | None, automatic: bool = False
) -> Calibration:
    """Run all guided stages and return a reviewed calibration."""
    session = WebcamCalibrationSession(config, camera_index)
    try:
        session.collect_stage(
            "1/6 Camera and hands",
            "Hold both hands like a steering wheel until tracking is stable.",
            lambda steering, roles: steering.raw_angle_degrees,
            4.0,
        )
        neutral = session.collect_stage(
            "2/6 Neutral",
            "Hold your comfortable straight position.",
            lambda steering, roles: steering.raw_angle_degrees,
            3.0,
        )
        if automatic:
            motion = session.collect_stage(
                "3/5 Automatic steering range",
                "Slowly rotate fully LEFT and RIGHT several times.",
                lambda steering, roles: steering.raw_angle_degrees,
                360.0,
            )
            ordered = sorted(motion)
            tail = max(5, len(ordered) // 4)
            left, right = ordered[:tail], ordered[-tail:]
        else:
            left = session.collect_stage(
                "3/6 Left",
                "Rotate the virtual wheel comfortably LEFT.",
                lambda steering, roles: steering.raw_angle_degrees,
                4.0,
            )
            right = session.collect_stage(
                "4/6 Right",
                "Rotate the virtual wheel comfortably RIGHT.",
                lambda steering, roles: steering.raw_angle_degrees,
                4.0,
            )

        def hand_height(steering: Any, roles: SteeringHands) -> float | None:
            del steering
            if not roles.valid_pair or not roles.steering_left or not roles.steering_right:
                return None
            if roles.steering_left.stale or roles.steering_right.stale:
                return None
            return statistics.mean(
                (
                    roles.steering_left.smoothed_reference_point.y,
                    roles.steering_right.smoothed_reference_point.y,
                )
            )

        acceleration = session.collect_stage(
            "5/6 Accelerator",
            "Hold both hands in your acceleration vertical region.",
            hand_height,
            0.035,
        )
        brake = session.collect_stage(
            "6/6 Brake",
            "Hold both hands in your braking vertical region.",
            hand_height,
            0.035,
        )
        count = int(config["calibration"]["samples_per_stage"])
        invert = bool(config["steering"]["invert"])
        minimum_samples = min(count, len(left), len(right))
        derived = derive_steering(neutral, left, right, invert, minimum_samples)
        accelerate_y, brake_y = derive_pedal_thresholds(acceleration, brake, count)
        diagnostics = session.camera.diagnostics
        tracking = config["hand_tracking"]
        calibration = Calibration(
            camera_index=diagnostics.index,
            requested_resolution=diagnostics.requested_resolution,
            actual_resolution=diagnostics.actual_resolution,
            preview_flip_horizontal=bool(config["camera"]["flip_horizontal"]),
            neutral_angle=derived.neutral_angle,
            maximum_left_angle=derived.calibrated_left_angle,
            maximum_right_angle=derived.calibrated_right_angle,
            dead_zone=derived.dead_zone,
            enter_left_threshold=derived.enter_left_threshold,
            exit_left_threshold=derived.exit_left_threshold,
            enter_right_threshold=derived.enter_right_threshold,
            exit_right_threshold=derived.exit_right_threshold,
            normalized_left_range=derived.normalized_left_range,
            normalized_right_range=derived.normalized_right_range,
            accelerate_y=accelerate_y,
            brake_y=brake_y,
            invert=invert,
            reference_point=str(tracking["reference_point"]),
            persistence_frames=int(tracking["persistence_frames"]),
            persistence_ms=float(tracking["persistence_ms"]),
            point_smoothing_alpha=float(tracking["point_smoothing_alpha"]),
        )
        calibration.validate()
        session.review(
            [
                f"Neutral {calibration.neutral_angle:+.1f}°",
                f"Range {calibration.maximum_left_angle:+.1f}° / "
                f"{calibration.maximum_right_angle:+.1f}°",
                f"Enter L/R {calibration.enter_left_threshold:+.1f}° / "
                f"{calibration.enter_right_threshold:+.1f}°",
                f"Pedal Y {calibration.accelerate_y:.3f} / {calibration.brake_y:.3f}",
            ]
        )
        return calibration
    finally:
        session.close()


def main() -> int:
    """Run webcam calibration, optionally falling back to explicit manual input."""
    parser = argparse.ArgumentParser(description="Webcam-assisted controller calibration")
    parser.add_argument("--output", type=Path, default=Path("data/calibration/default.yaml"))
    parser.add_argument("--config", type=Path, default=Path("config/default_config.yaml"))
    parser.add_argument("--camera-index", type=int)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--manual", action="store_true")
    parser.add_argument(
        "--automatic",
        action="store_true",
        help="Detect left/right range from one continuous motion stage",
    )
    args = parser.parse_args()
    try:
        config = load_yaml(args.config)
        if args.camera_index is not None:
            config["camera"]["index"] = args.camera_index
        validate_config(config)
        if args.manual:
            calibration = manual_calibration(config)
        else:
            try:
                calibration = webcam_calibration(config, args.camera_index, args.automatic)
            except CameraError as exc:
                print(f"Webcam calibration unavailable: {exc}")
                try:
                    fallback = input("Use explicit manual fallback? [y/N]: ").strip().lower()
                except EOFError:
                    fallback = "n"
                if fallback != "y":
                    return 1
                calibration = manual_calibration(config)
        save_calibration(args.output, calibration, args.force)
        print(f"Saved validated calibration to {args.output}")
        return 0
    except (CalibrationCancelled, KeyboardInterrupt):
        print("\nCalibration cancelled; no values were saved.")
        return 0
    except (ApplicationError, ImportError, OSError, ValueError) as exc:
        print(f"Calibration failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
