"""Validated CRUD and interchange for user-created game profiles."""

import shutil
from pathlib import Path
from typing import Any

import yaml

from src.controller.key_mapping import validate_mapping
from src.exceptions import ConfigurationError
from src.utils.file_handler import atomic_write_text
from src.utils.resources import user_config_directory

from .base_profile import ConfiguredGameProfile
from .profile_loader import load_profile


class ProfileStore:
    """Own editable profiles outside bundled application resources."""

    def __init__(self, directory: Path | None = None) -> None:
        self.directory = directory or user_config_directory() / "profiles"

    def save(self, profile: ConfiguredGameProfile, overwrite: bool = False) -> Path:
        """Validate and atomically save a profile."""
        profile_id = self._validate_id(profile.profile_id)
        path = self.directory / f"{profile_id}.yaml"
        if path.exists() and not overwrite:
            raise ConfigurationError(f"Profile already exists: {profile_id}")
        data: dict[str, Any] = {
            "game": {
                "id": profile_id,
                "name": profile.name,
                "platform": profile.platform,
            },
            "key_mapping": validate_mapping(profile.key_mapping),
            "sensitivity": profile.sensitivity_profile,
            "steering_limits": profile.steering_limits,
            "calibration": profile.calibration,
            "hud_branding": profile.hud_branding,
        }
        atomic_write_text(path, yaml.safe_dump(data, sort_keys=False))
        return path

    def list(self) -> dict[str, ConfiguredGameProfile]:
        """Load every valid user profile."""
        if not self.directory.exists():
            return {}
        profiles: dict[str, ConfiguredGameProfile] = {}
        for path in sorted(self.directory.glob("*.yaml")):
            loaded = load_profile(path)
            if not isinstance(loaded, ConfiguredGameProfile):
                raise ConfigurationError(f"Reserved profile id cannot be user-defined: {path}")
            profiles[loaded.profile_id] = loaded
        return profiles

    def duplicate(self, profile_id: str, new_id: str, new_name: str) -> Path:
        """Duplicate an existing user profile under a new identity."""
        profile = self._get(profile_id)
        return self.save(
            ConfiguredGameProfile(
                profile_id=self._validate_id(new_id),
                name=new_name,
                platform=profile.platform,
                key_mapping=dict(profile.key_mapping),
                sensitivity_profile=profile.sensitivity_profile,
                steering_limits=dict(profile.steering_limits),
                calibration=dict(profile.calibration),
                hud_branding=dict(profile.hud_branding),
            )
        )

    def delete(self, profile_id: str) -> None:
        """Delete one user profile."""
        path = self.directory / f"{self._validate_id(profile_id)}.yaml"
        if not path.exists():
            raise ConfigurationError(f"Unknown user profile: {profile_id}")
        path.unlink()

    def import_profile(self, source: Path, overwrite: bool = False) -> Path:
        """Validate and import a profile from YAML."""
        loaded = load_profile(source)
        profile = ConfiguredGameProfile(
            profile_id=loaded.profile_id,
            name=loaded.name,
            platform=loaded.platform,
            key_mapping=dict(loaded.key_mapping),
            sensitivity_profile=loaded.sensitivity_profile,
            steering_limits=dict(getattr(loaded, "steering_limits", {})),
            calibration=dict(getattr(loaded, "calibration", {})),
            hud_branding=dict(loaded.hud_branding),
        )
        return self.save(profile, overwrite=overwrite)

    def export_profile(self, profile_id: str, destination: Path) -> Path:
        """Export a profile to a caller-selected file."""
        source = self.directory / f"{self._validate_id(profile_id)}.yaml"
        if not source.exists():
            raise ConfigurationError(f"Unknown user profile: {profile_id}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        return destination

    def _get(self, profile_id: str) -> ConfiguredGameProfile:
        try:
            return self.list()[profile_id]
        except KeyError as exc:
            raise ConfigurationError(f"Unknown user profile: {profile_id}") from exc

    @staticmethod
    def _validate_id(profile_id: str) -> str:
        value = profile_id.strip().lower()
        allowed = "abcdefghijklmnopqrstuvwxyz0123456789_-"
        if not value or any(character not in allowed for character in value):
            raise ConfigurationError(
                "Profile id may contain only letters, numbers, underscores, and hyphens"
            )
        return value
