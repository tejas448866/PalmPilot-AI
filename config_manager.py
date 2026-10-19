"""Validated YAML configuration loading and default generation."""

import shutil
from pathlib import Path
from typing import Any

from src.exceptions import ConfigurationError

from .file_handler import load_yaml
from .validators import validate_config


class ConfigurationManager:
    """Load configuration with readable errors and safe default generation."""

    def __init__(self, template_path: Path = Path("config/default_config.yaml")) -> None:
        self.template_path = template_path

    def load(self, path: Path, generate_if_missing: bool = True) -> dict[str, Any]:
        """Load and validate YAML, optionally copying the maintained default."""
        if not path.exists():
            if not generate_if_missing:
                raise ConfigurationError(f"Configuration file does not exist: {path}")
            if not self.template_path.exists():
                raise ConfigurationError(
                    f"Cannot generate {path}; template is missing: {self.template_path}"
                )
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(self.template_path, path)
        try:
            config = load_yaml(path)
            validate_config(config)
            return config
        except (KeyError, TypeError, ValueError, OSError) as exc:
            raise ConfigurationError(f"Invalid configuration {path}: {exc}") from exc
