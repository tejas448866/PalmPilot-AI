"""Persist editable gesture-to-command mappings."""

from pathlib import Path

import yaml

from src.gesture import Command
from src.utils.file_handler import atomic_write_text


class GestureActionMapping:
    """Validated mapping between model labels and abstract commands."""

    def __init__(self, mappings: dict[str, tuple[Command, ...]] | None = None) -> None:
        self.mappings = mappings or {}

    @classmethod
    def load(cls, path: Path) -> "GestureActionMapping":
        """Load YAML mappings; a missing file means no ML actions."""
        if not path.exists():
            return cls()
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return cls.from_mapping(data)

    @classmethod
    def from_mapping(cls, data: object) -> "GestureActionMapping":
        """Validate a decoded YAML mapping."""
        if not isinstance(data, dict):
            raise ValueError("Gesture action configuration must be a mapping")
        raw_mappings = data.get("mappings", {})
        if not isinstance(raw_mappings, dict):
            raise ValueError("'mappings' must be a mapping")
        mappings: dict[str, tuple[Command, ...]] = {}
        for label, values in raw_mappings.items():
            actions = [values] if isinstance(values, str) else values
            if not isinstance(actions, list):
                raise ValueError(f"Actions for {label!r} must be a string or list")
            try:
                mappings[str(label)] = tuple(Command(str(action).lower()) for action in actions)
            except ValueError as exc:
                raise ValueError(f"Invalid action mapping for {label!r}: {exc}") from exc
        result = cls(mappings)
        result.validate()
        return result

    def validate(self) -> None:
        """Reject mappings that can activate conflicting pedals together."""
        for label, commands in self.mappings.items():
            if Command.ACCELERATE in commands and Command.BRAKE in commands:
                raise ValueError(f"Gesture {label!r} cannot map to both accelerate and brake")

    def commands_for(self, label: str) -> set[Command]:
        """Return abstract commands for a predicted label."""
        return set(self.mappings.get(label, ()))

    def set(self, label: str, commands: set[Command]) -> None:
        """Update one mapping."""
        if not label.strip():
            raise ValueError("Gesture label cannot be empty")
        self.mappings[label] = tuple(sorted(commands, key=lambda command: command.value))

    def save(self, path: Path) -> None:
        """Save mappings as human-editable YAML."""
        self.validate()
        atomic_write_text(
            path,
            yaml.safe_dump(
                {
                    "schema_version": 1,
                    "mappings": {
                        label: [command.value for command in commands]
                        for label, commands in sorted(self.mappings.items())
                    },
                },
                sort_keys=False,
            ),
        )
