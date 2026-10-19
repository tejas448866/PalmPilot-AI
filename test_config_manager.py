"""Configuration default generation and readable failure."""

import pytest

from src.exceptions import ConfigurationError
from src.utils.config_manager import ConfigurationManager


def test_missing_config_is_generated(tmp_path) -> None:
    target = tmp_path / "generated.yaml"
    config = ConfigurationManager().load(target)
    assert target.exists()
    assert config["application"]["dry_run"]


def test_missing_template_has_readable_error(tmp_path) -> None:
    with pytest.raises(ConfigurationError, match="template is missing"):
        ConfigurationManager(tmp_path / "none.yaml").load(tmp_path / "target.yaml")
