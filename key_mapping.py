"""Validate and resolve human-readable keyboard names."""

from typing import Any

from src.exceptions import InvalidKeyMappingError

NAMED_KEYS = {"up", "down", "left", "right", "space", "esc", "enter", "shift"}


def validate_key_name(name: str) -> str:
    """Return normalized supported key name or raise."""
    normalized = name.strip().lower()
    if normalized not in NAMED_KEYS and not (len(normalized) == 1 and normalized.isalnum()):
        raise InvalidKeyMappingError(f"Unsupported key name: {name!r}")
    return normalized


def resolve_key(name: str) -> Any:
    """Resolve a name to a pynput key value."""
    from pynput.keyboard import Key

    normalized = validate_key_name(name)
    return getattr(Key, normalized) if normalized in NAMED_KEYS else normalized


def validate_mapping(mapping: dict[str, str]) -> dict[str, str]:
    """Validate required actions and mutually exclusive key bindings."""
    required = {"accelerate", "brake", "left", "right"}
    missing = required - mapping.keys()
    if missing:
        raise InvalidKeyMappingError(f"Missing key mappings: {sorted(missing)}")
    normalized = {action: validate_key_name(name) for action, name in mapping.items()}
    for first, second in (("accelerate", "brake"), ("left", "right")):
        if normalized[first] == normalized[second]:
            raise InvalidKeyMappingError(
                f"Conflicting mappings: {first} and {second} both use {normalized[first]!r}"
            )
    return normalized
