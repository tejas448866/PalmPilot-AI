"""Filesystem game plugin discovery."""

from src.game_profiles import GameManager


def test_builtin_game_plugins_are_discovered() -> None:
    profiles = GameManager().discover()
    assert {
        "racing_limits",
        "euro_truck_simulator_2",
        "american_truck_simulator",
        "forza_horizon",
        "need_for_speed",
    } <= profiles.keys()
    assert profiles["forza_horizon"].sensitivity_profile == "pro"
    assert profiles["racing_limits"].hud_branding["title"] == "Racing Limits"
