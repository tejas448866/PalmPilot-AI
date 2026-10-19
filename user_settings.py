"""Validated, atomic per-user application settings."""

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from src.utils.file_handler import load_json, save_json
from src.utils.resources import user_config_directory


@dataclass
class UserSettings:
    """Small persistent state that must not modify bundled project files."""

    schema_version: int = 1
    first_run_completed: bool = False
    selected_camera_id: str = "camera-0"
    selected_profile_id: str = "generic_wasd"
    test_mode: bool = True
    theme: str = "Dark"
    layout_mode: str = "studio"
    window_geometry: str = ""
    last_working_browser_engine: str = ""

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> "UserSettings":
        """Validate and create settings from a JSON mapping."""
        if value.get("schema_version", 1) != 1:
            raise ValueError("Unsupported user settings schema version")
        selected_camera = value.get("selected_camera_id", "camera-0")
        selected_profile = value.get("selected_profile_id", "generic_wasd")
        theme = value.get("theme", "Dark")
        layout_mode = value.get("layout_mode", "studio")
        window_geometry = value.get("window_geometry", "")
        last_browser = value.get("last_working_browser_engine", "")
        for name, item in (
            ("selected_camera_id", selected_camera),
            ("selected_profile_id", selected_profile),
            ("theme", theme),
            ("layout_mode", layout_mode),
        ):
            if not isinstance(item, str) or not item.strip():
                raise ValueError(f"{name} must be a non-empty string")
        if layout_mode not in {"studio", "camera_focus", "compact"}:
            raise ValueError("layout_mode must be studio, camera_focus, or compact")
        if not isinstance(window_geometry, str):
            raise ValueError("window_geometry must be a string")
        if last_browser not in {"", "qt_webengine", "webview2"}:
            raise ValueError("last_working_browser_engine is invalid")
        return cls(
            first_run_completed=bool(value.get("first_run_completed", False)),
            selected_camera_id=selected_camera,
            selected_profile_id=selected_profile,
            test_mode=bool(value.get("test_mode", True)),
            theme=theme,
            layout_mode=layout_mode,
            window_geometry=window_geometry,
            last_working_browser_engine=last_browser,
        )


class UserSettingsStore:
    """Load and atomically persist user settings."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or user_config_directory() / "settings.json"

    def load(self) -> UserSettings:
        """Return defaults when the settings file does not exist."""
        if not self.path.exists():
            return UserSettings()
        try:
            return UserSettings.from_mapping(load_json(self.path))
        except (OSError, ValueError) as exc:
            raise ValueError(f"Invalid user settings {self.path}: {exc}") from exc

    def save(self, settings: UserSettings) -> None:
        """Validate and atomically persist settings."""
        validated = UserSettings.from_mapping(asdict(settings))
        save_json(self.path, asdict(validated))
