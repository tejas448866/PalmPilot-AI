"""Load and validate YAML game profiles."""

from pathlib import Path

from src.controller.key_mapping import validate_mapping
from src.utils.file_handler import load_yaml

from .base_profile import ConfiguredGameProfile, GameProfile
from .racing_limits_profile import RacingLimitsProfile


def load_profile(path: Path) -> GameProfile:
    """Load a game profile from YAML."""
    data = load_yaml(path)
    game = data.get("game", {})
    name = str(game.get("name", "Unknown game"))
    platform = str(game.get("platform", "Unknown platform"))
    mapping = validate_mapping(data.get("key_mapping", {}))
    profile_id = str(game.get("id", path.stem))
    if profile_id == "racing_limits":
        return RacingLimitsProfile(name, platform, mapping)
    return ConfiguredGameProfile(
        profile_id=profile_id,
        name=name,
        platform=platform,
        key_mapping=mapping,
        sensitivity_profile=str(data.get("sensitivity", "normal")),
        steering_limits={
            str(key): float(value) for key, value in data.get("steering_limits", {}).items()
        },
        calibration={str(key): float(value) for key, value in data.get("calibration", {}).items()},
        hud_branding={str(key): str(value) for key, value in data.get("hud_branding", {}).items()},
    )
