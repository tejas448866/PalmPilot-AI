"""Privacy-conscious local diagnostics export."""

import importlib.metadata
import platform
import sys
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src import __version__
from src.utils.file_handler import save_json

SENSITIVE_TERMS = ("password", "secret", "token", "credential", "api_key")


def sanitize(value: Any, key: str = "") -> Any:
    """Remove credentials while preserving useful diagnostic structure."""
    if any(term in key.lower() for term in SENSITIVE_TERMS):
        return "<redacted>"
    if isinstance(value, Mapping):
        return {str(item_key): sanitize(item, str(item_key)) for item_key, item in value.items()}
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    return value


def dependency_versions(
    names: tuple[str, ...] = ("opencv-python", "mediapipe", "pynput"),
) -> dict[str, str]:
    """Return installed versions without importing heavyweight packages."""
    versions: dict[str, str] = {}
    for name in names:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = "not installed"
    return versions


def export_diagnostics(
    output: Path,
    camera_config: Mapping[str, Any] | None = None,
    active_profile: str = "",
    log_path: Path | None = None,
    maximum_log_lines: int = 200,
    runtime_context: Mapping[str, Any] | None = None,
) -> Path:
    """Write a sanitized, bounded diagnostics report."""
    recent_logs: list[str] = []
    if log_path and log_path.exists():
        recent_logs = log_path.read_text(encoding="utf-8", errors="replace").splitlines()[
            -maximum_log_lines:
        ]
    report = {
        "application": {
            "name": "AI Hand Gesture Racing Controller",
            "version": __version__,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "system": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "frozen": bool(getattr(sys, "frozen", False)),
        },
        "dependencies": dependency_versions(),
        "camera": sanitize(dict(camera_config or {})),
        "active_profile": active_profile,
        "runtime": sanitize(dict(runtime_context or {})),
        "recent_logs": recent_logs,
        "privacy": "Local diagnostics only; credentials and personal files are excluded.",
    }
    save_json(output, report)
    return output
