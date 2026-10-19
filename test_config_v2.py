"""Version 2 visualization and calibration configuration."""

from src.utils.file_handler import load_yaml
from src.utils.validators import validate_config


def test_default_config_has_valid_part2_fields() -> None:
    config = load_yaml(__import__("pathlib").Path("config/default_config.yaml"))
    validate_config(config)
    assert config["visualization"]["landmark_radius"] >= 5
    assert config["visualization"]["show_performance_metrics"]
    assert config["visualization"]["preview_width"] == 480
    assert config["visualization"]["preview_height"] == 270
    assert config["calibration"]["samples_per_stage"] >= 10
