"""Configuration validation and merging."""

from copy import deepcopy
from typing import Any
from urllib.parse import urlparse

from src.exceptions import ConfigurationError


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge mappings without mutating inputs."""
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def validate_config(config: dict[str, Any]) -> None:
    """Validate essential ranges and required sections."""
    required = (
        "application",
        "camera",
        "hand_tracking",
        "steering",
        "gestures",
        "smoothing",
        "controller",
        "visualization",
        "recording",
    )
    missing = [name for name in required if name not in config]
    if missing:
        raise ConfigurationError(f"Missing configuration sections: {missing}")
    if int(config["camera"]["index"]) < 0:
        raise ConfigurationError("camera.index must be non-negative")
    for key in ("min_detection_confidence", "min_tracking_confidence"):
        value = float(config["hand_tracking"][key])
        if not 0.0 <= value <= 1.0:
            raise ConfigurationError(f"hand_tracking.{key} must be in [0, 1]")
    if int(config["camera"]["requested_width"]) < 1:
        raise ConfigurationError("camera.requested_width must be positive")
    if float(config["camera"]["preview_scale"]) <= 0:
        raise ConfigurationError("camera.preview_scale must be positive")
    if int(config["hand_tracking"]["max_num_hands"]) != 2:
        raise ConfigurationError("Version 2 requires hand_tracking.max_num_hands=2")
    alpha = float(config["hand_tracking"]["point_smoothing_alpha"])
    if not 0.0 < alpha <= 1.0:
        raise ConfigurationError("point_smoothing_alpha must be in (0, 1]")
    for section in ("hand_tracking", "steering"):
        if float(config[section]["one_euro_min_cutoff"]) <= 0:
            raise ConfigurationError(f"{section}.one_euro_min_cutoff must be positive")
        if float(config[section]["one_euro_beta"]) < 0:
            raise ConfigurationError(f"{section}.one_euro_beta cannot be negative")
    if config["steering"]["response_curve"] not in {
        "linear",
        "cubic",
        "exponential",
        "sigmoid",
    }:
        raise ConfigurationError("steering.response_curve is unsupported")
    confidence = float(config["hand_tracking"]["minimum_gesture_confidence"])
    if not 0 <= confidence <= 1:
        raise ConfigurationError("minimum_gesture_confidence must be in [0, 1]")
    visualization = config["visualization"]
    if not 0 < float(visualization["panel_alpha"]) <= 1:
        raise ConfigurationError("visualization.panel_alpha must be in (0, 1]")
    if float(visualization["ui_scale"]) <= 0:
        raise ConfigurationError("visualization.ui_scale must be positive")
    if int(visualization.get("preview_width", 480)) < 160:
        raise ConfigurationError("visualization.preview_width must be at least 160")
    if int(visualization.get("preview_height", 270)) < 90:
        raise ConfigurationError("visualization.preview_height must be at least 90")
    if "calibration" not in config or int(config["calibration"]["samples_per_stage"]) < 10:
        raise ConfigurationError("calibration.samples_per_stage must be at least 10")
    if config["accessibility"]["steering_mode"] not in {"single_hand", "two_hand"}:
        raise ConfigurationError("accessibility.steering_mode is invalid")
    if config["accessibility"]["handed_mode"] not in {"any", "left", "right"}:
        raise ConfigurationError("accessibility.handed_mode is invalid")
    hybrid = config["gestures"].get("hybrid", {})
    if hybrid:
        if not 90 <= float(hybrid["extension_angle_degrees"]) <= 180:
            raise ConfigurationError("hybrid extension angle must be in [90, 180]")
        if not 0 < float(hybrid["folded_tip_distance"]) < float(hybrid["extended_tip_distance"]):
            raise ConfigurationError("hybrid folded distance must be below extended distance")
        for key in (
            "clear_gesture_frames",
            "ml_gesture_frames",
            "action_switch_frames",
            "ambiguous_release_frames",
            "hand_lost_release_frames",
        ):
            if int(hybrid[key]) < 1:
                raise ConfigurationError(f"gestures.hybrid.{key} must be positive")
    machine_learning = config.get("machine_learning", {})
    threshold = float(machine_learning.get("confidence_threshold", 0.65))
    if not 0 <= threshold <= 1:
        raise ConfigurationError("machine_learning.confidence_threshold must be in [0, 1]")
    if int(machine_learning.get("smoothing_window", 5)) < 1:
        raise ConfigurationError("machine_learning.smoothing_window must be positive")
    if float(machine_learning.get("dataset_capture_interval_seconds", 0.9)) < 0.1:
        raise ConfigurationError(
            "machine_learning.dataset_capture_interval_seconds must be at least 0.1"
        )
    if float(machine_learning.get("dataset_minimum_feature_distance", 0.015)) < 0:
        raise ConfigurationError(
            "machine_learning.dataset_minimum_feature_distance cannot be negative"
        )
    ui = config.get("ui", {})
    if ui.get("default_layout", "studio") not in {
        "studio",
        "camera_focus",
        "compact",
    }:
        raise ConfigurationError("ui.default_layout is invalid")
    if int(ui.get("min_window_width", 1100)) < 900:
        raise ConfigurationError("ui.min_window_width must be at least 900")
    if int(ui.get("min_window_height", 700)) < 600:
        raise ConfigurationError("ui.min_window_height must be at least 600")
    game = config.get("game", {})
    game_url = str(game.get("launch_url", "https://www.crazygames.com/game/racing-limits"))
    parsed_url = urlparse(game_url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise ConfigurationError("game.launch_url must be an HTTP(S) URL")
    if game.get("integration_mode", "auto") not in {
        "auto",
        "embedded",
        "qt_webengine",
        "webview2",
        "external",
    }:
        raise ConfigurationError("game.integration_mode is invalid")
    if game.get("preferred_embedded_engine", "qt_webengine") not in {
        "qt_webengine",
        "webview2",
    }:
        raise ConfigurationError("game.preferred_embedded_engine is invalid")
    for key in (
        "external_fallback_enabled",
        "remember_browser_session",
        "allow_fullscreen",
    ):
        if not isinstance(game.get(key, True), bool):
            raise ConfigurationError(f"game.{key} must be boolean")
