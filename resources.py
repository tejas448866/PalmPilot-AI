"""Development, packaged-resource, and per-user data paths."""

import os
import shutil
import sys
from pathlib import Path


def application_root() -> Path:
    """Return the bundled extraction root or source repository root."""
    bundled_root = getattr(sys, "_MEIPASS", None)
    if isinstance(bundled_root, str):
        return Path(bundled_root)
    return Path(__file__).resolve().parents[2]


def resource_path(relative_path: str | Path) -> Path:
    """Resolve an application resource in source and PyInstaller builds."""
    return application_root() / relative_path


def user_config_directory() -> Path:
    """Return the writable per-user configuration directory."""
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / "AIHandGestureRacingController"
    return Path.home() / ".config" / "AIHandGestureRacingController"


def editable_config_path(name: str) -> Path:
    """Copy a bundled default into per-user storage on first use."""
    destination = user_config_directory() / "config" / name
    if not destination.exists():
        source = resource_path(Path("config") / name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    return destination
