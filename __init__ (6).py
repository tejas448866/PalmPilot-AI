"""Optional game workspace integration."""

from .browser_base import BrowserState, EmbeddedBrowser, LoadingState
from .browser_factory import (
    QT_RACING_LIMITS_UNSUPPORTED_REASON,
    BrowserSelection,
    create_embedded_browser,
    qt_webengine_available,
    select_browser_engine,
    webview2_runtime_available,
    webview2_unavailable_reason,
)
from .browser_workspace import (
    BrowserWorkspaceManager,
    IntegrationDecision,
    select_integration_mode,
    validate_game_url,
    webengine_available,
)
from .qt_webengine_browser import qt_webengine_version
from .webview2_browser import webview2_runtime_path, webview2_runtime_version

__all__ = [
    "BrowserWorkspaceManager",
    "IntegrationDecision",
    "select_integration_mode",
    "validate_game_url",
    "webengine_available",
    "BrowserSelection",
    "QT_RACING_LIMITS_UNSUPPORTED_REASON",
    "BrowserState",
    "EmbeddedBrowser",
    "LoadingState",
    "create_embedded_browser",
    "qt_webengine_available",
    "qt_webengine_version",
    "select_browser_engine",
    "webview2_runtime_available",
    "webview2_unavailable_reason",
    "webview2_runtime_path",
    "webview2_runtime_version",
]
