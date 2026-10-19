"""CLI and real-time application orchestration."""

import argparse
import logging
import time
from collections.abc import Callable, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.calibration.calibration_manager import apply_calibration
from src.calibration.calibration_storage import load_calibration
from src.camera import (
    CameraManager,
    CameraRegistry,
    CameraSource,
    FrameProcessor,
    MultiCameraManager,
    scale_preview,
)
from src.camera.auto_tuner import CameraRecommendation, analyze_camera
from src.controller import CommandManager, KeyboardController
from src.controller.emergency_stop import is_stop_key, preview_window_closed
from src.exceptions import ApplicationError, RecordingError
from src.game_profiles import GameManager, load_profile
from src.gesture import (
    Command,
    DeterministicGesture,
    HybridGestureConfig,
    HybridGesturePolicy,
    LandmarkGestureClassifier,
    LandmarkGestureConfig,
)
from src.gesture.accelerator_detector import AcceleratorDetector
from src.gesture.auxiliary_gesture_detector import AuxiliaryGestureDetector
from src.gesture.brake_detector import BrakeDetector
from src.gesture.gesture_detector import GestureDetector
from src.gesture.steering_detector import SteeringDetector
from src.gesture.steering_profiles import load_steering_profiles
from src.hand_tracking.hand_detector import HandDetector
from src.hand_tracking.landmark_extractor import LandmarkExtractor
from src.hand_tracking.role_tracker import HandRoleTracker
from src.ml import (
    GestureActionMapping,
    GestureInferenceEngine,
    RecognitionDiagnostics,
    resolve_mapped_actions,
    resolve_model_path,
    select_pedal_command,
)
from src.performance import PerformanceMonitor, PerformanceSnapshot, SessionStatistics
from src.recording import ScreenshotManager, SessionRecorder, VideoRecorder
from src.recording.replay import replay_session
from src.smoothing import CommandStabilizer
from src.utils.config_manager import ConfigurationManager
from src.utils.file_handler import load_yaml
from src.utils.logger import configure_logging
from src.utils.resources import resource_path
from src.utils.runtime_settings import RuntimeSettings
from src.utils.validators import deep_merge, validate_config
from src.visualization import OverlayRenderer, VisualizationSettings

LOGGER = logging.getLogger(__name__)

RESOURCE_CONFIG_PATHS = (
    ("steering", "sensitivity_profiles_file"),
    ("machine_learning", "model_path"),
    ("machine_learning", "metadata_path"),
    ("machine_learning", "action_mapping"),
    ("logging", "config_file"),
)


def build_parser() -> argparse.ArgumentParser:
    """Create the public command-line interface."""
    parser = argparse.ArgumentParser(
        description="Control a browser racing game with webcam hand gestures."
    )
    parser.add_argument("--config", type=Path, default=Path("config/default_config.yaml"))
    parser.add_argument("--profile", type=Path, default=Path("config/racing_limits.yaml"))
    parser.add_argument("--calibration", type=Path)
    parser.add_argument("--camera-index", type=int)
    parser.add_argument("--dry-run", action="store_true", help="Never emit keyboard events")
    parser.add_argument(
        "--live", action="store_true", help="Enable real keyboard events (verify dry-run first)"
    )
    parser.add_argument("--no-preview", action="store_true")
    parser.add_argument("--record", action="store_true")
    parser.add_argument("--record-session", action="store_true")
    parser.add_argument("--replay-session", type=Path)
    parser.add_argument("--debug", action="store_true")
    return parser


def load_runtime_config(args: argparse.Namespace) -> dict[str, Any]:
    """Load YAML and apply CLI overrides."""
    config = ConfigurationManager().load(args.config)
    profile_data = load_yaml(args.profile)
    for section in (
        "camera",
        "steering",
        "gestures",
        "smoothing",
        "controller",
        "visualization",
        "recording",
    ):
        if section in profile_data:
            config[section] = deep_merge(config.get(section, {}), profile_data[section])
    if args.camera_index is not None:
        config["camera"]["index"] = args.camera_index
    if args.live and args.dry_run:
        raise ValueError("--live and --dry-run are mutually exclusive")
    if args.live:
        config["application"]["dry_run"] = False
    if args.dry_run:
        config["application"]["dry_run"] = True
    if args.no_preview:
        config["visualization"]["enabled"] = False
    if args.record:
        config["recording"]["enabled"] = True
    if args.record_session:
        config["recording"]["record_session"] = True
    if args.debug:
        config["application"]["debug"] = True
    calibration = load_calibration(args.calibration)
    if args.calibration is not None:
        apply_calibration(config, calibration)
    resolve_runtime_resource_paths(config)
    validate_config(config)
    return config


def resolve_runtime_resource_paths(config: dict[str, Any]) -> None:
    """Resolve bundled read-only resources independently of the working directory."""
    for section, key in RESOURCE_CONFIG_PATHS:
        value = config.get(section, {}).get(key)
        if not isinstance(value, str) or not value:
            continue
        configured = Path(value)
        if configured.is_absolute():
            continue
        bundled = resource_path(configured)
        if bundled.exists():
            config[section][key] = str(bundled)


class RacingControllerApplication:
    """Own all real-time components and guarantee cleanup."""

    def __init__(
        self,
        config: dict[str, Any],
        profile_path: Path,
        calibration_loaded: bool = False,
        runtime_settings: RuntimeSettings | None = None,
        status_callback: Callable[[str], None] | None = None,
        frame_callback: Callable[[Any, dict[str, Any]], None] | None = None,
        preview_mode: str = "standalone",
    ) -> None:
        self.config = config
        self.profile = load_profile(profile_path)
        self.calibration_loaded = calibration_loaded
        self.runtime_settings = runtime_settings
        self.status_callback = status_callback
        self.frame_callback = frame_callback
        if preview_mode not in {"standalone", "integrated", "disabled"}:
            raise ValueError("preview_mode must be standalone, integrated, or disabled")
        self.preview_mode = preview_mode

    def _report_status(self, status: str) -> None:
        """Publish lightweight lifecycle status to GUI callers."""
        LOGGER.info("Controller status: %s", status)
        if self.status_callback:
            self.status_callback(status)

    def run(self) -> None:
        """Initialize the pipeline and run until an emergency-stop event."""
        import cv2

        cfg = self.config
        camera_cfg, tracking_cfg = cfg["camera"], cfg["hand_tracking"]
        accessibility_cfg = cfg["accessibility"]
        flip_horizontal = bool(accessibility_cfg.get("mirror_mode", camera_cfg["flip_horizontal"]))
        steering_cfg, threshold_cfg = cfg["steering"], cfg["gestures"]["thresholds"]
        active_profile_key = str(steering_cfg.get("sensitivity_profile", "normal")).lower()
        dry_run = bool(cfg["application"]["dry_run"])
        preview = bool(cfg["visualization"]["enabled"]) and self.preview_mode == "standalone"
        keyboard = KeyboardController(dry_run=dry_run)
        manager = CommandManager(
            keyboard,
            self.profile.key_mapping,
            float(cfg["controller"]["lost_tracking_release_timeout"]),
        )
        camera: MultiCameraManager | None = None
        detector: HandDetector | None = None
        recorder: VideoRecorder | None = None
        session_recorder: SessionRecorder | None = None
        camera_recommendation: CameraRecommendation | None = None
        statistics = SessionStatistics.create()
        session_started = time.perf_counter()
        shutdown_reason = "normal exit"
        try:
            self._report_status("initializing camera")
            camera_registry = CameraRegistry()
            camera_sources = camera_registry.configured(list(camera_cfg["sources"]))
            if camera_cfg.get("automatic_detection"):
                known = {source.capture_source for source in camera_sources}
                camera_sources.extend(
                    source
                    for source in camera_registry.enumerate_local()
                    if source.capture_source not in known
                )

            def create_camera(source: CameraSource) -> CameraManager:
                return CameraManager(
                    source.capture_source,
                    int(camera_cfg["requested_width"]),
                    int(camera_cfg["requested_height"]),
                    int(camera_cfg["fps"]),
                    source.backend_order or list(camera_cfg["backend_order"]),
                    list(camera_cfg["fallback_resolutions"]),
                    int(camera_cfg["processing_width"]),
                    float(camera_cfg["preview_scale"]),
                    int(camera_cfg["warmup_frames"]),
                    camera_cfg.get("autofocus"),
                    camera_cfg.get("exposure"),
                )

            camera = MultiCameraManager(
                camera_sources,
                create_camera,
                camera_registry,
                str(camera_cfg.get("preferred_source_id", "")) or None,
                int(camera_cfg["reconnect_attempts"]),
            )
            self._report_status(
                "camera ready "
                f"({camera.diagnostics.backend}, "
                f"{camera.diagnostics.actual_resolution[0]}x"
                f"{camera.diagnostics.actual_resolution[1]})"
            )
            self._report_status("initializing MediaPipe")
            detector = HandDetector(
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
            self._report_status("MediaPipe ready")
            processor = FrameProcessor(flip_horizontal, camera.diagnostics.processing_resolution)
            extractor = LandmarkExtractor()
            role_tracker = HandRoleTracker(
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
                | {
                    "nominal_frequency": float(camera_cfg["fps"]),
                    "handed_mode": str(accessibility_cfg["handed_mode"]),
                }
            )
            steering_detector = SteeringDetector(
                **{
                    key: value
                    for key, value in steering_cfg.items()
                    if key
                    in {
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
                    }
                }
                | {
                    "nominal_frequency": float(camera_cfg["fps"]),
                    "minimum_confidence": float(tracking_cfg["minimum_gesture_confidence"]),
                    "steering_mode": str(accessibility_cfg["steering_mode"]),
                    "handed_mode": str(accessibility_cfg["handed_mode"]),
                }
            )
            steering_profiles = load_steering_profiles(
                Path(steering_cfg["sensitivity_profiles_file"])
            )
            steering_detector.apply_profile(steering_profiles[active_profile_key])
            role_tracker.tune_filter(
                steering_profiles[active_profile_key].min_cutoff,
                steering_profiles[active_profile_key].beta,
            )
            gesture_detector = GestureDetector(
                AcceleratorDetector(float(threshold_cfg["accelerate_y"])),
                BrakeDetector(float(threshold_cfg["brake_y"])),
            )
            auxiliary_cfg = cfg["gestures"]["auxiliary"]
            auxiliary_detector = AuxiliaryGestureDetector(
                dict(auxiliary_cfg["enabled"]),
                float(auxiliary_cfg["pinch_distance"]),
                float(auxiliary_cfg["open_hand_distance"]),
            )
            ml_cfg = cfg.get("machine_learning", {})
            ml_engine = None
            ml_mapping = GestureActionMapping()
            ml_requested = bool(ml_cfg.get("enabled", False))
            fallback_to_rules = bool(ml_cfg.get("fallback_to_rule_based", True))
            model_path = resolve_model_path(Path(str(ml_cfg.get("model_path", ""))))
            metadata_path = resolve_model_path(Path(str(ml_cfg.get("metadata_path", ""))))
            mapping_path = resolve_model_path(Path(str(ml_cfg.get("action_mapping", ""))))
            LOGGER.info(
                "Resolved ML config: enabled=%s model=%s metadata=%s mapping=%s "
                "threshold=%.2f smoothing_window=%d fallback_to_rules=%s",
                ml_requested,
                model_path,
                metadata_path,
                mapping_path,
                float(ml_cfg.get("confidence_threshold", 0.55)),
                int(ml_cfg.get("smoothing_window", 3)),
                fallback_to_rules,
            )
            ml_mapping = GestureActionMapping.load(mapping_path)
            LOGGER.info(
                "Gesture action mapping loaded from %s: open_palm=%s closed_fist=%s",
                mapping_path,
                sorted(command.value for command in ml_mapping.commands_for("open_palm")),
                sorted(command.value for command in ml_mapping.commands_for("closed_fist")),
            )
            if ml_requested:
                try:
                    ml_engine = GestureInferenceEngine(
                        model_path=model_path,
                        metadata_path=metadata_path,
                        confidence_threshold=float(ml_cfg["confidence_threshold"]),
                        smoothing_window=int(ml_cfg["smoothing_window"]),
                    )
                    LOGGER.info(
                        "ML model loaded: path=%s algorithm=%s labels=%s features=%d",
                        ml_engine.model_path,
                        ml_engine.algorithm,
                        ml_engine.classes,
                        ml_engine.extractor.feature_count,
                    )
                except Exception as exc:
                    LOGGER.exception("ML startup failed: %s", exc)
                    if not fallback_to_rules:
                        raise ApplicationError(
                            f"ML mode requested but startup failed: {exc}"
                        ) from exc
            ml_active = ml_engine is not None
            hybrid_cfg = cfg["gestures"].get("hybrid", {})
            hybrid_active = bool(hybrid_cfg.get("enabled", True))
            landmark_classifier = LandmarkGestureClassifier(
                LandmarkGestureConfig(
                    **{
                        key: hybrid_cfg[key]
                        for key in (
                            "extension_angle_degrees",
                            "fold_angle_degrees",
                            "extended_tip_distance",
                            "folded_tip_distance",
                            "open_openness_threshold",
                            "closed_openness_threshold",
                            "open_extended_fingers",
                            "closed_folded_fingers",
                            "open_max_folded_fingers",
                            "closed_max_extended_fingers",
                            "open_exit_extended_fingers",
                            "closed_exit_folded_fingers",
                            "open_exit_openness_threshold",
                            "closed_exit_openness_threshold",
                        )
                    }
                )
            )
            hybrid_policy = HybridGesturePolicy(
                HybridGestureConfig(
                    **{
                        key: hybrid_cfg[key]
                        for key in (
                            "clear_gesture_frames",
                            "ml_gesture_frames",
                            "ambiguous_release_frames",
                            "hand_lost_release_frames",
                            "action_switch_frames",
                        )
                    }
                )
            )
            recognition = RecognitionDiagnostics(
                "Hybrid" if hybrid_active else "Rule-based", ml_active
            )
            last_recognition_log: tuple[str, str, str | None] | None = None
            pedal_stabilizer = CommandStabilizer(
                int(cfg["smoothing"].get("pedal_stable_frames", 3)), Command.IDLE
            )
            renderer = OverlayRenderer(
                bool(cfg["visualization"]["draw_landmarks"]),
                bool(cfg["visualization"]["draw_status"]),
                VisualizationSettings(
                    **{
                        key: cfg["visualization"][key]
                        for key in (
                            "ui_scale",
                            "landmark_radius",
                            "palm_landmark_radius",
                            "connection_thickness",
                            "steering_line_thickness",
                            "panel_alpha",
                            "show_camera_diagnostics",
                            "show_performance_metrics",
                            "show_raw_angle",
                            "show_smoothed_angle",
                            "show_wheel_circle",
                            "show_confidence_bar",
                            "show_recommendations",
                        )
                    }
                ),
            )
            monitor = PerformanceMonitor(int(cfg["diagnostics"]["performance_window"]))
            metrics = PerformanceSnapshot()
            screenshots = ScreenshotManager(Path("output/screenshots"))
            if cfg["recording"]["enabled"]:
                recorder = VideoRecorder(
                    Path(cfg["recording"]["output_directory"]),
                    str(cfg["recording"]["codec"]),
                    float(cfg["recording"]["fps"]),
                )
            if cfg["recording"].get("record_session", False):
                session_recorder = SessionRecorder(
                    Path(cfg["recording"]["session_directory"]),
                    str(cfg["recording"]["codec"]),
                    float(cfg["recording"]["fps"]),
                )
            window_name = str(cfg["visualization"]["window_name"])
            if preview:
                _prepare_preview_window(
                    cv2,
                    window_name,
                    int(cfg["visualization"].get("preview_width", 480)),
                    int(cfg["visualization"].get("preview_height", 270)),
                    int(cfg["visualization"].get("preview_x", 20)),
                    int(cfg["visualization"].get("preview_y", 60)),
                )
            LOGGER.info(
                "Started %s mode for %s", "dry-run" if dry_run else "LIVE", self.profile.name
            )
            preview_started = False
            preview_raise_frames = 0
            while True:
                runtime_changes = (
                    self.runtime_settings.consume_changes() if self.runtime_settings else {}
                )
                if runtime_changes.get("emergency_stop"):
                    manager.shutdown()
                    shutdown_reason = "GUI emergency stop"
                    LOGGER.warning("Emergency stop requested; all active keys released")
                    break
                if runtime_changes.get("shutdown_requested"):
                    manager.shutdown()
                    shutdown_reason = "GUI stop request"
                    break
                requested_profile = runtime_changes.get("steering.profile")
                if requested_profile in steering_profiles:
                    active_profile_key = str(requested_profile)
                    profile = steering_profiles[active_profile_key]
                    steering_detector.apply_profile(profile)
                    role_tracker.tune_filter(profile.min_cutoff, profile.beta)
                if runtime_changes.get("camera.next"):
                    source = camera.switch_next()
                    processor = FrameProcessor(
                        flip_horizontal,
                        camera.diagnostics.processing_resolution,
                    )
                    LOGGER.info("Camera switched to %s", source.name)
                requested_game = runtime_changes.get("game.profile")
                if requested_game:
                    game_profile = GameManager().get(str(requested_game))
                    manager.shutdown()
                    manager.mapping = game_profile.key_mapping
                    self.profile = game_profile
                frame_started = time.perf_counter()
                stage_started = time.perf_counter()
                captured = camera.read()
                capture_seconds = time.perf_counter() - stage_started
                processed = processor.process(captured)
                stage_started = time.perf_counter()
                raw_result = detector.process(processed.rgb)
                inference_seconds = time.perf_counter() - stage_started
                stage_started = time.perf_counter()
                height, width = processed.bgr.shape[:2]
                hands = extractor.extract(raw_result, width, height, processed.timestamp)
                steering_hands = role_tracker.update(hands)
                hand_seconds = time.perf_counter() - stage_started
                stage_started = time.perf_counter()
                steering = steering_detector.detect(steering_hands)
                steering_command = steering.command
                if hybrid_active:
                    rule_based_pedal = Command.IDLE
                    auxiliary: set[Command] = set()
                else:
                    rule_based_pedal = pedal_stabilizer.update(gesture_detector.detect_pedal(hands))
                    auxiliary = auxiliary_detector.detect(hands)
                pedal = select_pedal_command(hybrid_active, Command.IDLE, rule_based_pedal)
                if hybrid_active and hands.hands:
                    preferred = hands.by_handedness(str(ml_cfg.get("inference_hand", "right")))
                    inference_hand = preferred or hands.hands[0]
                    landmark_result = landmark_classifier.classify(inference_hand)
                    prediction = None
                    ml_gesture = None
                    if (
                        landmark_result.gesture is DeterministicGesture.AMBIGUOUS
                        and ml_active
                        and ml_engine
                    ):
                        prediction = ml_engine.predict(inference_hand)
                        ml_gesture = prediction.label if prediction.known else None
                    elif ml_engine:
                        ml_engine.reset()
                    decision = hybrid_policy.update(
                        landmark_result.gesture,
                        ml_gesture,
                        True,
                        landmark_result.supporting_gesture,
                    )
                    mapped = ml_mapping.commands_for(decision.final_gesture)
                    resolved_actions = resolve_mapped_actions(mapped)
                    pedal = select_pedal_command(True, resolved_actions.pedal, rule_based_pedal)
                    if resolved_actions.steering:
                        steering_command = resolved_actions.steering
                    auxiliary |= set(resolved_actions.auxiliary)
                    mapped_name = (
                        ",".join(sorted(command.value for command in mapped)) if mapped else "idle"
                    )
                    recognition = RecognitionDiagnostics(
                        "Hybrid",
                        ml_active,
                        prediction.raw_label if prediction else "not_used",
                        prediction.label if prediction else "not_used",
                        prediction.confidence if prediction else 1.0,
                        mapped_name,
                        decision.reason,
                        True,
                        landmark_result.finger_states,
                        landmark_result.openness_score,
                        landmark_result.gesture.value,
                        ml_gesture or "none",
                        decision.final_gesture,
                        decision.stability_frames,
                    )
                    log_state = (
                        landmark_result.gesture.value,
                        f"{decision.final_gesture}:{mapped_name}",
                        decision.reason,
                    )
                    if log_state != last_recognition_log:
                        LOGGER.info(
                            "Hybrid gesture deterministic=%s openness=%.2f fingers=%s "
                            "ml=%s final=%s stability=%d mapped=%s reason=%s",
                            landmark_result.gesture.value,
                            landmark_result.openness_score,
                            landmark_result.finger_states,
                            ml_gesture or "none",
                            decision.final_gesture,
                            decision.stability_frames,
                            mapped_name,
                            decision.reason,
                        )
                        last_recognition_log = log_state
                elif hybrid_active:
                    if ml_engine:
                        ml_engine.reset()
                    decision = hybrid_policy.update(
                        DeterministicGesture.AMBIGUOUS,
                        None,
                        False,
                    )
                    mapped = ml_mapping.commands_for(decision.final_gesture)
                    resolved_actions = resolve_mapped_actions(mapped)
                    pedal = resolved_actions.pedal
                    recognition = RecognitionDiagnostics(
                        "Hybrid",
                        ml_active,
                        mapped_action=(
                            ",".join(sorted(command.value for command in mapped))
                            if mapped
                            else "idle"
                        ),
                        rejection_reason=decision.reason,
                        hand_detected=False,
                        deterministic_gesture="no_hand",
                        final_gesture=decision.final_gesture,
                        stability_frames=decision.stability_frames,
                    )
                    last_recognition_log = None
                if Command.RESET_CALIBRATION in auxiliary:
                    steering_detector.neutral_angle = 0.0
                    auxiliary.discard(Command.RESET_CALIBRATION)
                    LOGGER.info("Gesture reset neutral calibration to zero")
                control_tracking_visible = steering.valid or (
                    hybrid_active and (bool(hands.hands) or decision.final_gesture != "idle")
                )
                manager.apply(
                    steering_command,
                    pedal,
                    control_tracking_visible,
                    auxiliary=auxiliary,
                )
                steering_seconds = time.perf_counter() - stage_started
                stage_started = time.perf_counter()
                rendered = renderer.render(
                    processed.bgr,
                    hands,
                    steering,
                    pedal,
                    metrics,
                    keyboard.active_keys,
                    dry_run,
                    bool(recorder and recorder.active),
                    self.calibration_loaded,
                    steering_hands,
                    camera.diagnostics,
                    camera_recommendation.message if camera_recommendation else None,
                    recognition,
                )
                render_seconds = time.perf_counter() - stage_started
                metrics = monitor.update(
                    frame_started,
                    {
                        "capture": capture_seconds,
                        "inference": inference_seconds,
                        "hand_processing": hand_seconds,
                        "steering": steering_seconds,
                        "render": render_seconds,
                    },
                )
                statistics.update(
                    metrics.fps,
                    steering.confidence,
                    steering.normalized_steering_value,
                    steering.valid,
                    processed.timestamp,
                    steering.profile_name,
                )
                interval = int(cfg["diagnostics"]["camera_recommendation_interval_frames"])
                if metrics.frames % interval == 0:
                    camera_recommendation = analyze_camera(
                        processed.bgr,
                        camera.diagnostics,
                        metrics.fps,
                        metrics.latency_ms,
                    )
                if recorder and not recorder.active:
                    try:
                        recorder.start((width, height))
                    except RecordingError:
                        LOGGER.exception("Recording disabled after initialization failure")
                        recorder = None
                if recorder:
                    recorder.write(rendered)
                if session_recorder and session_recorder.paths is None:
                    session_recorder.start(
                        (width, height),
                        steering.profile_name,
                        None,
                        asdict(camera.diagnostics),
                    )
                if session_recorder:
                    session_recorder.write(rendered, processed.timestamp, steering, pedal)
                if self.frame_callback:
                    self.frame_callback(
                        rendered,
                        build_runtime_state(
                            recognition=recognition,
                            steering=steering,
                            pedal=pedal,
                            metrics=metrics,
                            active_keys=keyboard.active_keys,
                            dry_run=dry_run,
                            hands_detected=len(hands.hands),
                            camera_diagnostics=camera.diagnostics,
                            profile_name=self.profile.name,
                        ),
                    )
                if preview:
                    try:
                        cv2.imshow(
                            window_name,
                            scale_preview(rendered, float(camera_cfg["preview_scale"])),
                        )
                    except cv2.error as exc:
                        raise ApplicationError(
                            "OpenCV could not create the controller preview window. "
                            f"Build information GUI backend: {_opencv_gui_backend(cv2)}. "
                            f"Original error: {exc}"
                        ) from exc
                    if not preview_started:
                        preview_started = True
                        preview_raise_frames = 15
                        _set_preview_topmost(cv2, window_name, True)
                        self._report_status("preview ready")
                    elif preview_raise_frames > 0:
                        preview_raise_frames -= 1
                        if preview_raise_frames == 0:
                            _set_preview_topmost(cv2, window_name, False)
                    key_code = cv2.waitKey(1)
                    if is_stop_key(key_code) or preview_window_closed(window_name):
                        shutdown_reason = "preview emergency stop"
                        break
                    if key_code & 0xFF in (ord("s"), ord("S"), ord("p"), ord("P")):
                        LOGGER.info("Saved screenshot: %s", screenshots.save(rendered))
                    profile_keys = {
                        ord("1"): "easy",
                        ord("2"): "normal",
                        ord("3"): "pro",
                    }
                    selected = profile_keys.get(key_code & 0xFF)
                    if selected and selected in steering_profiles:
                        active_profile_key = selected
                        profile = steering_profiles[selected]
                        steering_detector.apply_profile(profile)
                        role_tracker.tune_filter(profile.min_cutoff, profile.beta)
                        LOGGER.info("Steering profile switched to %s", profile.name)
                    if key_code & 0xFF in (ord("c"), ord("C")):
                        source = camera.switch_next()
                        processor = FrameProcessor(
                            flip_horizontal,
                            camera.diagnostics.processing_resolution,
                        )
                        LOGGER.info("Camera switched to %s", source.name)
        except KeyboardInterrupt:
            shutdown_reason = "KeyboardInterrupt"
        finally:
            manager.shutdown()
            if recorder:
                try:
                    recorder.stop()
                except Exception:
                    LOGGER.exception("Video recorder cleanup failed")
            if session_recorder:
                try:
                    session_recorder.stop()
                except Exception:
                    LOGGER.exception("Session recorder cleanup failed")
            if detector:
                try:
                    detector.close()
                except Exception:
                    LOGGER.exception("Hand detector cleanup failed")
            if camera:
                if cfg["session_reports"]["enabled"]:
                    try:
                        report = statistics.save(
                            Path(cfg["session_reports"]["output_directory"]),
                            time.perf_counter() - session_started,
                            asdict(camera.diagnostics),
                            (
                                steering_detector.profile_name
                                if "steering_detector" in locals()
                                else active_profile_key
                            ),
                        )
                        LOGGER.info("Session report: %s", report)
                    except OSError:
                        LOGGER.exception("Could not save session report")
                try:
                    camera.release()
                except Exception:
                    LOGGER.exception("Camera cleanup failed")
            try:
                cv2.destroyAllWindows()
            except Exception:
                LOGGER.exception("OpenCV window cleanup failed")
            LOGGER.info("Shutdown complete (%s); all active keys released", shutdown_reason)
            self._report_status("stopped")


def build_runtime_state(
    recognition: RecognitionDiagnostics,
    steering: Any,
    pedal: Command,
    metrics: PerformanceSnapshot,
    active_keys: set[str],
    dry_run: bool,
    hands_detected: int,
    camera_diagnostics: Any,
    profile_name: str,
) -> dict[str, Any]:
    """Build the truthful controller state consumed by desktop presentation."""
    gesture = recognition.final_gesture or recognition.deterministic_gesture or "idle"
    return {
        "gesture": gesture,
        "action": pedal.value,
        "confidence": float(recognition.confidence),
        "tracking": hands_detected > 0,
        "hands_detected": hands_detected,
        "fps": float(metrics.fps),
        "latency_ms": float(metrics.latency_ms),
        "steering_value": float(steering.normalized_steering_value),
        "steering_command": steering.command.value,
        "pedal": pedal.value,
        "active_keys": tuple(sorted(active_keys)),
        "dry_run": dry_run,
        "camera_index": camera_diagnostics.index,
        "camera_backend": camera_diagnostics.backend,
        "actual_resolution": tuple(camera_diagnostics.actual_resolution),
        "processing_resolution": camera_diagnostics.processing_resolution,
        "recognizer_mode": recognition.mode,
        "profile_name": profile_name,
    }


def _opencv_gui_backend(cv2_module: Any) -> str:
    """Extract the configured OpenCV GUI backend for actionable diagnostics."""
    for line in cv2_module.getBuildInformation().splitlines():
        if line.strip().startswith("GUI:"):
            return line.split(":", 1)[1].strip()
    return "unknown"


def _set_preview_topmost(cv2_module: Any, window_name: str, enabled: bool) -> None:
    """Raise a newly created HighGUI preview, then return it to normal z-order."""
    try:
        cv2_module.setWindowProperty(
            window_name,
            cv2_module.WND_PROP_TOPMOST,
            1.0 if enabled else 0.0,
        )
        LOGGER.info("Preview topmost=%s", enabled)
    except (AttributeError, cv2_module.error):
        LOGGER.warning("OpenCV backend does not support preview z-order control", exc_info=True)


def _prepare_preview_window(
    cv2_module: Any,
    window_name: str,
    width: int,
    height: int,
    x: int,
    y: int,
) -> None:
    """Create one compact, aspect-safe, user-resizable desktop preview."""
    flags = cv2_module.WINDOW_NORMAL
    if hasattr(cv2_module, "WINDOW_KEEPRATIO"):
        flags |= cv2_module.WINDOW_KEEPRATIO
    try:
        cv2_module.namedWindow(window_name, flags)
        cv2_module.resizeWindow(window_name, width, height)
        cv2_module.moveWindow(window_name, x, y)
        LOGGER.info(
            "Prepared resizable preview: size=%dx%d position=(%d,%d)",
            width,
            height,
            x,
            y,
        )
    except cv2_module.error as exc:
        raise ApplicationError(
            "OpenCV could not prepare the resizable controller preview. "
            f"GUI backend: {_opencv_gui_backend(cv2_module)}. Original error: {exc}"
        ) from exc


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.replay_session:
            return replay_session(args.replay_session)
        config = load_runtime_config(args)
        configure_logging(
            Path(config["logging"]["config_file"]), bool(config["application"]["debug"])
        )
        RacingControllerApplication(
            config,
            args.profile,
            calibration_loaded=bool(args.calibration and args.calibration.exists()),
        ).run()
        return 0
    except (ApplicationError, OSError, ValueError) as exc:
        logging.getLogger(__name__).error("%s", exc)
        return 1
