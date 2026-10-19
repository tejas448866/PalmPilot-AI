"""Failure-tolerant browser launch and Windows side-by-side arrangement."""

import ctypes
import importlib.util
import logging
import webbrowser
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlparse

LOGGER = logging.getLogger(__name__)


def validate_game_url(value: str) -> str:
    """Return a safe HTTP(S) game URL or raise a readable error."""
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Game URL must be an absolute http or https URL")
    return value


def webengine_available() -> bool:
    """Check optional Qt WebEngine availability without importing it."""
    return importlib.util.find_spec("PySide6.QtWebEngineWidgets") is not None


@dataclass(frozen=True)
class IntegrationDecision:
    """Selected game presentation mode and its honest rationale."""

    mode: str
    reason: str


def select_integration_mode(requested: str, webengine: bool) -> IntegrationDecision:
    """Prefer the reliable external-browser path unless embedding is explicit."""
    if requested not in {"auto", "external", "embedded"}:
        raise ValueError("Integration mode must be auto, external, or embedded")
    if requested == "embedded" and webengine:
        return IntegrationDecision("embedded", "Qt WebEngine is available")
    if requested == "embedded":
        return IntegrationDecision(
            "external", "Qt WebEngine is unavailable; using the system browser"
        )
    if requested == "auto":
        return IntegrationDecision(
            "external",
            "External browser selected for reliable WebGL, audio, keyboard, and fullscreen",
        )
    return IntegrationDecision("external", "External browser selected by configuration")


class WindowBackend(Protocol):
    """Minimal native-window operations used by the workspace manager."""

    def find_window(self, title_hint: str) -> int | None: ...

    def arrange_side_by_side(self, dashboard: int, game: int) -> bool: ...

    def focus(self, handle: int) -> bool: ...


class WindowsWindowBackend:
    """Small ctypes adapter; no background polling or injected browser code."""

    def find_window(self, title_hint: str) -> int | None:
        user32 = ctypes.windll.user32
        found: list[int] = []
        hint = title_hint.casefold()

        @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        def callback(handle: int, _parameter: int) -> bool:
            if not user32.IsWindowVisible(handle):
                return True
            length = user32.GetWindowTextLengthW(handle)
            if length:
                buffer = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(handle, buffer, length + 1)
                if hint in buffer.value.casefold():
                    found.append(int(handle))
                    return False
            return True

        user32.EnumWindows(callback, 0)
        return found[0] if found else None

    def arrange_side_by_side(self, dashboard: int, game: int) -> bool:
        user32 = ctypes.windll.user32
        width = int(user32.GetSystemMetrics(0))
        height = int(user32.GetSystemMetrics(1))
        left_width = max(640, int(width * 0.42))
        return bool(
            user32.MoveWindow(dashboard, 0, 0, left_width, height, True)
            and user32.MoveWindow(game, left_width, 0, width - left_width, height, True)
        )

    def focus(self, handle: int) -> bool:
        user32 = ctypes.windll.user32
        user32.ShowWindow(handle, 9)
        return bool(user32.SetForegroundWindow(handle))


class BrowserWorkspaceManager:
    """Launch and arrange an external game window on explicit user actions."""

    def __init__(
        self,
        game_url: str,
        title_hint: str,
        backend: WindowBackend | None = None,
        opener: Callable[[str], bool] | None = None,
    ) -> None:
        self.game_url = validate_game_url(game_url)
        self.title_hint = title_hint
        self.backend = backend or WindowsWindowBackend()
        self.opener = opener or webbrowser.open
        self.game_handle: int | None = None

    def launch(self) -> str:
        """Open the configured URL without pretending the browser is embedded."""
        if not self.opener(self.game_url):
            raise RuntimeError("The system browser did not accept the game launch request")
        return "Game launched in the system browser"

    def locate(self) -> int | None:
        """Locate a matching visible browser window when Windows exposes one."""
        self.game_handle = self.backend.find_window(self.title_hint)
        return self.game_handle

    def arrange(self, dashboard_handle: int) -> str:
        """Arrange both windows, returning a concise user-facing status."""
        handle = self.game_handle or self.locate()
        if handle is None:
            return "Browser window not found yet; open the game, then try Arrange Windows"
        if not self.backend.arrange_side_by_side(dashboard_handle, handle):
            return "Windows could not arrange the dashboard and game"
        return "Dashboard and game arranged side by side"

    def focus_game(self) -> str:
        """Focus the located game without changing controller state."""
        handle = self.game_handle or self.locate()
        if handle is None:
            return "Browser window not found"
        return "Game focused" if self.backend.focus(handle) else "Windows denied focus request"
