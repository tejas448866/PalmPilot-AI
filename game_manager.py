"""Filesystem-discovered game plugin manager."""

from pathlib import Path

from src.controller.key_mapping import validate_mapping
from src.exceptions import ConfigurationError
from src.utils.file_handler import load_yaml
from src.utils.resources import resource_path

from .base_profile import ConfiguredGameProfile, GameProfile


class GameManager:
    """Discover game folders without imports or core-code registration."""

    def __init__(self, plugins_directory: Path | None = None) -> None:
        self.plugins_directory = plugins_directory or resource_path("plugins")
        self._profiles: dict[str, GameProfile] = {}

    def discover(self) -> dict[str, GameProfile]:
        """Load every valid `game.yaml` one level beneath plugins."""
        profiles: dict[str, GameProfile] = {}
        if not self.plugins_directory.exists():
            return profiles
        for manifest in sorted(self.plugins_directory.glob("*/game.yaml")):
            data = load_yaml(manifest)
            game = data.get("game", {})
            profile_id = str(game.get("id", manifest.parent.name))
            if profile_id in profiles:
                raise ConfigurationError(f"Duplicate game plugin id: {profile_id}")
            profiles[profile_id] = ConfiguredGameProfile(
                profile_id=profile_id,
                name=str(game.get("name", profile_id)),
                platform=str(game.get("platform", "Windows")),
                key_mapping=validate_mapping(data.get("key_mapping", {})),
                sensitivity_profile=str(data.get("sensitivity", "normal")),
                steering_limits={
                    key: float(value) for key, value in data.get("steering_limits", {}).items()
                },
                calibration={
                    key: float(value) for key, value in data.get("calibration", {}).items()
                },
                hud_branding={
                    str(key): str(value) for key, value in data.get("hud_branding", {}).items()
                },
            )
        self._profiles = profiles
        return dict(profiles)

    def get(self, profile_id: str) -> GameProfile:
        """Return a discovered profile by stable identifier."""
        if not self._profiles:
            self.discover()
        try:
            return self._profiles[profile_id]
        except KeyError as exc:
            raise ConfigurationError(f"Unknown game profile: {profile_id}") from exc
