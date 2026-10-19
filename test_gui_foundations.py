"""GUI-independent theme and real-time configuration smoke tests."""

import os

import pytest

from src.gui import THEMES, stylesheet
from src.utils.runtime_settings import RuntimeSettings


def test_all_themes_generate_stylesheets() -> None:
    assert set(THEMES) == {"Dark", "Light", "Blue", "Cyber", "Racing"}
    assert all("QWidget" in stylesheet(name) for name in THEMES)
    assert all("}}" not in stylesheet(name) for name in THEMES)


def test_qt_accepts_every_stylesheet_without_parse_warning() -> None:
    pytest.importorskip("PySide6")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import qInstallMessageHandler
    from PySide6.QtWidgets import QApplication, QLineEdit, QPlainTextEdit, QPushButton, QWidget

    messages: list[str] = []

    def handler(message_type: object, context: object, message: str) -> None:
        del message_type, context
        messages.append(message)

    app = QApplication.instance() or QApplication([])
    previous = qInstallMessageHandler(handler)
    try:
        for name in THEMES:
            app.setStyleSheet(stylesheet(name))
            page = QWidget()
            controls = [QLineEdit(page), QPlainTextEdit(page), QPushButton("Visible", page)]
            page.show()
            app.processEvents()
            assert all(
                control.palette().color(control.foregroundRole()).isValid() for control in controls
            )
    finally:
        qInstallMessageHandler(previous)
    assert not any("Could not parse application stylesheet" in message for message in messages)


def test_runtime_settings_publish_and_consume() -> None:
    settings = RuntimeSettings()
    observed: list[tuple[str, object]] = []
    settings.subscribe(lambda key, value: observed.append((key, value)))
    settings.set("steering.profile", "pro")
    assert settings.get("steering.profile") == "pro"
    assert settings.consume_changes() == {"steering.profile": "pro"}
    assert settings.consume_changes() == {}
    assert observed == [("steering.profile", "pro")]
