"""Embedded-browser selection without hard Qt imports."""

import importlib.util
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .browser_base import EmbeddedBrowser
from .qt_webengine_browser import create_qt_webengine_browser_class
from .webview2_browser import (
    create_webview2_browser_class,
    webview2_runtime_path,
)

QT_RACING_LIMITS_UNSUPPORTED_REASON = (
    "Qt WebEngine is unsupported for Racing Limits because its MP4A audio "
    "buffers cannot be decoded by the distributed Qt build"
)


def qt_webengine_available() -> bool:
    """Return whether both required Qt WebEngine modules are importable."""
    return (
        importlib.util.find_spec("PySide6.QtWebEngineCore") is not None
        and importlib.util.find_spec("PySide6.QtWebEngineWidgets") is not None
    )


def webview2_runtime_available() -> bool:
    """Return whether a supported native WebView2 adapter is installed."""
    return (
        importlib.util.find_spec("qtwebview2") is not None and webview2_runtime_path() is not None
    )


def webview2_unavailable_reason() -> str:
    """Describe the exact missing Windows WebView2 requirement."""
    if importlib.util.find_spec("qtwebview2") is None:
        return "The optional qtwebview2 adapter is not installed"
    if webview2_runtime_path() is None:
        return "Microsoft WebView2 Runtime is not installed"
    return ""


@dataclass(frozen=True)
class BrowserSelection:
    """Factory decision with a user-facing fallback reason."""

    engine: str
    reason: str


def select_browser_engine(
    requested_mode: str,
    preferred_engine: str,
    last_working_engine: str,
    qt_available: bool,
    webview2_available: bool,
    external_fallback_enabled: bool,
) -> BrowserSelection:
    """Select the supported Racing Limits production engine."""
    del preferred_engine, last_working_engine, qt_available
    if requested_mode == "embedded":
        requested_mode = "auto"
    if requested_mode == "external":
        return BrowserSelection("external", "External browser selected")
    if requested_mode == "qt_webengine":
        if external_fallback_enabled:
            return BrowserSelection("external", QT_RACING_LIMITS_UNSUPPORTED_REASON)
        return BrowserSelection("unavailable", QT_RACING_LIMITS_UNSUPPORTED_REASON)
    if webview2_available:
        return BrowserSelection("webview2", "Microsoft WebView2 selected for Racing Limits")
    reason = webview2_unavailable_reason() or "Microsoft WebView2 is unavailable"
    if external_fallback_enabled:
        return BrowserSelection("external", reason)
    return BrowserSelection("unavailable", f"{reason}; external browser fallback is disabled")


def create_embedded_browser(
    selection: BrowserSelection,
    parent: Any,
    requested_mode: str,
    user_data_path: Path,
    allow_fullscreen: bool,
    qt_factory: Callable[[], type] = create_qt_webengine_browser_class,
    webview2_factory: Callable[[], type] = create_webview2_browser_class,
) -> EmbeddedBrowser:
    """Construct the selected embedded implementation."""
    if selection.engine == "qt_webengine":
        browser_class = qt_factory()
        return browser_class(parent, requested_mode, user_data_path, allow_fullscreen)
    if selection.engine == "webview2":
        browser_class = webview2_factory()
        return browser_class(parent, requested_mode, user_data_path, allow_fullscreen)
    raise RuntimeError(selection.reason)
