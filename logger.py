"""Logging setup."""

import logging
import logging.config
import platform
import sys
import traceback
from datetime import datetime
from pathlib import Path
from types import TracebackType

import yaml

from .resources import user_config_directory


def log_directory() -> Path:
    """Return a writable log directory in source and frozen execution."""
    if getattr(sys, "frozen", False):
        return user_config_directory() / "logs"
    return Path("logs")


def configure_logging(config_path: Path, debug: bool = False) -> None:
    """Configure logging from YAML, ensuring runtime directories exist."""
    logs = log_directory()
    logs.mkdir(parents=True, exist_ok=True)
    if config_path.exists():
        with config_path.open(encoding="utf-8") as stream:
            configuration = yaml.safe_load(stream)
        if getattr(sys, "frozen", False):
            handlers = configuration.get("handlers", {})
            file_handler = handlers.get("file")
            if isinstance(file_handler, dict):
                file_handler["filename"] = str(logs / "controller.log")
        logging.config.dictConfig(configuration)
    else:
        logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
    logging.getLogger(__name__).info(
        "System: %s | Python: %s | machine: %s",
        platform.platform(),
        platform.python_version(),
        platform.machine(),
    )
    sys.excepthook = _crash_handler


def _crash_handler(
    exception_type: type[BaseException],
    exception: BaseException,
    traceback_object: TracebackType | None,
) -> None:
    """Write a local crash report and forward to Python's standard hook."""
    if issubclass(exception_type, KeyboardInterrupt):
        sys.__excepthook__(exception_type, exception, traceback_object)
        return
    crash_directory = log_directory() / "crashes"
    crash_directory.mkdir(parents=True, exist_ok=True)
    path = crash_directory / f"crash_{datetime.now():%Y%m%d_%H%M%S}.log"
    report = [
        f"Platform: {platform.platform()}",
        f"Python: {platform.python_version()}",
        "",
        "".join(traceback.format_exception(exception_type, exception, traceback_object)),
    ]
    path.write_text("\n".join(report), encoding="utf-8")
    logging.getLogger(__name__).critical("Unhandled crash report: %s", path)
    sys.__excepthook__(exception_type, exception, traceback_object)
