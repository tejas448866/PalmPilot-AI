"""YAML and JSON file helpers."""

import json
import os
import tempfile
from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML mapping."""
    with path.open(encoding="utf-8") as stream:
        value = yaml.safe_load(stream) or {}
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a mapping")
    return value


def save_json(path: Path, value: dict[str, Any]) -> None:
    """Atomically save JSON after ensuring its directory."""
    atomic_write_text(path, json.dumps(value, indent=2))


def load_json(path: Path) -> dict[str, Any]:
    """Load a JSON mapping."""
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return value


def atomic_write_text(path: Path, content: str) -> None:
    """Replace a text file atomically without exposing a partial write."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)
