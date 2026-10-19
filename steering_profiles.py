"""Validated steering sensitivity profiles."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.utils.file_handler import load_yaml


@dataclass(frozen=True)
class SteeringProfile:
    """Hot-switchable steering response and filter parameters."""

    name: str
    dead_zone: float
    maximum_angle: float
    response_curve: str
    curve_strength: float
    min_cutoff: float
    beta: float


def load_steering_profiles(path: Path) -> dict[str, SteeringProfile]:
    """Load named sensitivity profiles from YAML."""
    data: dict[str, Any] = load_yaml(path)
    profiles: dict[str, SteeringProfile] = {}
    for name, values in data.get("profiles", {}).items():
        profile = SteeringProfile(name, **values)
        if profile.dead_zone < 0 or profile.maximum_angle <= profile.dead_zone:
            raise ValueError(f"Invalid steering profile {name}")
        if profile.response_curve not in {"linear", "cubic", "exponential", "sigmoid"}:
            raise ValueError(f"Invalid response curve in profile {name}")
        profiles[name.lower()] = profile
    if not profiles:
        raise ValueError("At least one steering profile is required")
    return profiles
