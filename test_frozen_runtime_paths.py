"""Frozen executable path and preview-diagnostic regression tests."""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.main import (
    _opencv_gui_backend,
    _prepare_preview_window,
    _set_preview_topmost,
    load_runtime_config,
)
from src.utils.logger import log_directory


def arguments(config: Path, profile: Path) -> SimpleNamespace:
    """Build the public CLI argument shape used by configuration loading."""
    return SimpleNamespace(
        config=config,
        profile=profile,
        calibration=None,
        camera_index=None,
        dry_run=True,
        live=False,
        no_preview=False,
        record=False,
        record_session=False,
        debug=False,
    )


def test_nested_runtime_resources_are_absolute_outside_project_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = Path(__file__).resolve().parents[2]
    monkeypatch.chdir(tmp_path)
    config = load_runtime_config(
        arguments(
            root / "config" / "default_config.yaml",
            root / "config" / "racing_limits.yaml",
        )
    )
    for section, key in (
        ("steering", "sensitivity_profiles_file"),
        ("machine_learning", "model_path"),
        ("machine_learning", "metadata_path"),
        ("machine_learning", "action_mapping"),
        ("logging", "config_file"),
    ):
        path = Path(config[section][key])
        assert path.is_absolute()
        assert path.exists()


def test_frozen_logs_use_per_user_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert log_directory() == tmp_path / "AIHandGestureRacingController" / "logs"


def test_opencv_preview_error_reports_gui_backend() -> None:
    fake_cv2 = SimpleNamespace(
        getBuildInformation=lambda: "Video I/O:\n  GUI: WIN32UI\nOther: value"
    )
    assert _opencv_gui_backend(fake_cv2) == "WIN32UI"


def test_preview_is_raised_then_returned_to_normal_z_order() -> None:
    calls: list[tuple[str, int, float]] = []
    fake_cv2 = SimpleNamespace(
        WND_PROP_TOPMOST=9,
        error=RuntimeError,
        setWindowProperty=lambda name, prop, value: calls.append((name, prop, value)),
    )
    _set_preview_topmost(fake_cv2, "Preview", True)
    _set_preview_topmost(fake_cv2, "Preview", False)
    assert calls == [("Preview", 9, 1.0), ("Preview", 9, 0.0)]


def test_preview_is_compact_resizable_and_movable() -> None:
    calls: list[tuple[object, ...]] = []
    fake_cv2 = SimpleNamespace(
        WINDOW_NORMAL=0,
        WINDOW_KEEPRATIO=0,
        error=RuntimeError,
        namedWindow=lambda *args: calls.append(("named", *args)),
        resizeWindow=lambda *args: calls.append(("resize", *args)),
        moveWindow=lambda *args: calls.append(("move", *args)),
    )
    _prepare_preview_window(fake_cv2, "Preview", 480, 270, 20, 60)
    assert calls == [
        ("named", "Preview", 0),
        ("resize", "Preview", 480, 270),
        ("move", "Preview", 20, 60),
    ]
