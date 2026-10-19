"""Racing Limits game-profile plugin."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RacingLimitsProfile:
    """Current Racing Limits keyboard-control profile."""

    name: str = "Racing Limits"
    platform: str = "CrazyGames (browser)"
    key_mapping: dict[str, str] = field(
        default_factory=lambda: {
            "accelerate": "up",
            "brake": "down",
            "left": "left",
            "right": "right",
        }
    )
    profile_id: str = "racing_limits"
    sensitivity_profile: str = "normal"
    steering_limits: dict[str, float] = field(default_factory=dict)
    calibration: dict[str, float] = field(default_factory=dict)
    hud_branding: dict[str, str] = field(
        default_factory=lambda: {"title": "Racing Limits", "accent": "#ffb020"}
    )


def default_racing_limits_profile() -> RacingLimitsProfile:
    """Return documented fallback arrow-key controls."""
    return RacingLimitsProfile()
