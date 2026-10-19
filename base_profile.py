"""Extensible game-profile contract and generic YAML implementation."""

from dataclasses import dataclass, field
from typing import Protocol


class GameProfile(Protocol):
    """Interface implemented by every supported game profile plugin."""

    @property
    def profile_id(self) -> str:
        """Stable profile identifier."""
        ...

    @property
    def name(self) -> str:
        """Display game name."""
        ...

    @property
    def platform(self) -> str:
        """Target platform."""
        ...

    @property
    def key_mapping(self) -> dict[str, str]:
        """Logical action to keyboard mapping."""
        ...

    @property
    def sensitivity_profile(self) -> str:
        """Recommended steering sensitivity profile."""
        ...

    @property
    def hud_branding(self) -> dict[str, str]:
        """Brand colors and title."""
        ...


@dataclass(frozen=True)
class ConfiguredGameProfile:
    """Data-driven profile requiring no game-specific control duplication."""

    profile_id: str
    name: str
    platform: str
    key_mapping: dict[str, str]
    sensitivity_profile: str = "normal"
    steering_limits: dict[str, float] = field(default_factory=dict)
    calibration: dict[str, float] = field(default_factory=dict)
    hud_branding: dict[str, str] = field(default_factory=dict)
