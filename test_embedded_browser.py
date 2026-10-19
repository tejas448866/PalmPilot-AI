"""Embedded-browser selection, state, and Qt host tests."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from src.game_integration import (
    QT_RACING_LIMITS_UNSUPPORTED_REASON,
    BrowserSelection,
    BrowserState,
    LoadingState,
    create_embedded_browser,
    select_browser_engine,
)


def test_auto_browser_selection_uses_webview2_even_if_qt_was_last() -> None:
    selected = select_browser_engine("auto", "qt_webengine", "qt_webengine", True, True, True)
    assert selected.engine == "webview2"
    assert selected.reason == "Microsoft WebView2 selected for Racing Limits"


def test_auto_browser_selection_falls_back_external_without_webview2() -> None:
    fallback = select_browser_engine("auto", "qt_webengine", "", True, False, True)
    assert fallback.engine == "external"
    assert "WebView2" in fallback.reason


def test_legacy_embedded_mode_uses_webview2_policy() -> None:
    selected = select_browser_engine("embedded", "qt_webengine", "", True, True, True)
    assert selected.engine == "webview2"


def test_qt_webengine_is_not_selected_for_racing_limits() -> None:
    selected = select_browser_engine("qt_webengine", "qt_webengine", "", True, True, True)
    assert selected.engine == "external"
    assert selected.reason == QT_RACING_LIMITS_UNSUPPORTED_REASON


def test_missing_webview2_without_fallback_is_unavailable() -> None:
    unavailable = select_browser_engine("webview2", "webview2", "", False, False, False)
    assert unavailable.engine == "unavailable"


def test_missing_webview2_runtime_reports_reason_and_uses_external(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.game_integration import browser_factory

    monkeypatch.setattr(browser_factory.importlib.util, "find_spec", lambda _name: object())
    monkeypatch.setattr(browser_factory, "webview2_runtime_path", lambda: None)

    assert browser_factory.webview2_unavailable_reason() == (
        "Microsoft WebView2 Runtime is not installed"
    )
    selected = browser_factory.select_browser_engine(
        "auto",
        "webview2",
        "",
        False,
        False,
        True,
    )
    assert selected == BrowserSelection(
        "external",
        "Microsoft WebView2 Runtime is not installed",
    )


def test_browser_state_diagnostics_are_complete(tmp_path: Path) -> None:
    state = BrowserState(
        requested_mode="auto",
        selected_engine="qt_webengine",
        loading_state=LoadingState.LOADED,
        initialization_succeeded=True,
        current_url="https://example.com",
        load_succeeded=True,
        supports_webgl=True,
        supports_audio=True,
        supports_fullscreen=True,
        user_data_path=tmp_path,
    )
    report = state.diagnostics()
    assert report["selected_browser_engine"] == "qt_webengine"
    assert report["embedded_loading_state"] == "loaded"
    assert report["embedded_initialization_result"] is True
    assert report["webgl_capability"] is True
    assert report["browser_user_data_path"] == str(tmp_path)


def test_qt_factory_constructs_selected_adapter(tmp_path: Path) -> None:
    created: list[tuple[object, str, Path, bool]] = []

    class FakeBrowser:
        def __init__(self, parent: object, requested: str, path: Path, fullscreen: bool) -> None:
            created.append((parent, requested, path, fullscreen))

    parent = object()
    browser = create_embedded_browser(
        BrowserSelection("qt_webengine", "test"),
        parent,
        "auto",
        tmp_path,
        True,
        qt_factory=lambda: FakeBrowser,
    )
    assert isinstance(browser, FakeBrowser)
    assert created == [(parent, "auto", tmp_path, True)]


def test_webview2_factory_owns_host_lifecycle(tmp_path: Path) -> None:
    created: list[tuple[object, str, Path, bool]] = []

    class FakeWebView2:
        def __init__(self, parent: object, requested: str, path: Path, fullscreen: bool) -> None:
            created.append((parent, requested, path, fullscreen))

    parent = object()
    browser = create_embedded_browser(
        BrowserSelection("webview2", "test"),
        parent,
        "webview2",
        tmp_path,
        True,
        webview2_factory=lambda: FakeWebView2,
    )
    assert isinstance(browser, FakeWebView2)
    assert created == [(parent, "webview2", tmp_path, True)]


def test_game_workspace_switches_to_embedded_view(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication, QLabel

    from src.gui.dashboard import create_dashboard_class

    _app = QApplication.instance() or QApplication([])
    dashboard = create_dashboard_class()("studio")
    browser_widget = QLabel("real browser surface")
    dashboard.set_browser_widget(browser_widget, "Microsoft WebView2")
    assert dashboard.game_stack.currentWidget() is dashboard.browser_host
    assert dashboard.browser_host_layout.indexOf(browser_widget) == 0
    assert dashboard.external_window_controls.isHidden()
    dashboard.update_browser_state(
        SimpleNamespace(
            loading_state=LoadingState.LOADING,
            selected_engine="webview2",
            load_progress=42,
            last_error="",
        )
    )
    assert dashboard.load_progress.isHidden() is False
    assert dashboard.load_progress.value() == 42
    assert dashboard.browser_engine.text() == "Microsoft WebView2"
    dashboard.update_browser_state(
        SimpleNamespace(
            loading_state=LoadingState.FAILED,
            selected_engine="webview2",
            load_progress=100,
            last_error="load failed",
        )
    )
    assert dashboard.game_stack.currentWidget() is dashboard.browser_error
    assert not dashboard.external_window_controls.isHidden()
