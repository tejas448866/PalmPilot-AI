"""Windows WebView2 adapter using a genuine Qt-owned child control."""

import logging
import platform
import time
from pathlib import Path
from typing import Any

from .browser_base import BrowserState, LoadingState

LOGGER = logging.getLogger(__name__)


def webview2_runtime_path() -> Path | None:
    """Locate the installed Evergreen WebView2 Runtime without using Edge Stable."""
    if platform.system() != "Windows":
        return None
    roots = (
        Path(r"C:\Program Files (x86)\Microsoft\EdgeWebView\Application"),
        Path(r"C:\Program Files\Microsoft\EdgeWebView\Application"),
    )
    candidates: list[Path] = []
    for root in roots:
        if root.exists():
            candidates.extend(root.glob("*/msedgewebview2.exe"))
    return sorted(candidates)[-1] if candidates else None


def webview2_runtime_version() -> str:
    """Return the installed runtime directory version."""
    executable = webview2_runtime_path()
    return executable.parent.name if executable else "unavailable"


def create_webview2_browser_class() -> type:
    """Create the optional QtWebView2 implementation lazily."""
    from PySide6.QtCore import QObject, Signal
    from qtwebview2 import QtWebView2Widget

    class WebView2Browser(QObject):
        """Adapter around a WebView2 HWND genuinely owned by a Qt host widget."""

        state_changed = Signal(object)
        navigation_started = Signal(str)
        fullscreen_requested = Signal(bool)
        crashed = Signal(str)
        _navigation_completed_signal = Signal(bool, str)
        _navigation_started_signal = Signal(str)
        _process_failed_signal = Signal(str)

        def __init__(
            self,
            parent: Any,
            requested_mode: str,
            user_data_path: Path,
            allow_fullscreen: bool = True,
        ) -> None:
            super().__init__(parent)
            if webview2_runtime_path() is None:
                raise RuntimeError("Microsoft WebView2 Runtime is not installed")
            user_data_path.mkdir(parents=True, exist_ok=True)
            self.state = BrowserState(
                requested_mode=requested_mode,
                selected_engine="webview2",
                loading_state=LoadingState.READY,
                supports_fullscreen=allow_fullscreen,
                supports_audio=True,
                supports_webgl=True,
                user_data_path=user_data_path,
            )
            self._load_started_at = 0.0
            self.widget = QtWebView2Widget(
                url=None,
                debug=False,
                context_menus=False,
                handle_new_window=False,
                lazyload=True,
                user_data_folder=str(user_data_path),
                fullscreen_support=False,
                parent=parent,
            )
            self.widget.bridge.initialization_done.connect(self._initialized)
            self.widget.bridge.domContentLoaded.connect(self._dom_loaded)
            self._navigation_completed_signal.connect(self._navigation_completed)
            self._navigation_started_signal.connect(self._navigation_started)
            self._process_failed_signal.connect(self._process_failed)

        def _emit_state(self) -> None:
            self.state_changed.emit(self.state)

        def _initialized(self, succeeded: bool, error: str) -> None:
            self.state.initialization_succeeded = succeeded
            if not succeeded:
                self.state.loading_state = LoadingState.FAILED
                self.state.last_error = error or "WebView2 initialization failed"
                self._emit_state()
                return
            core = self.widget._webview.CoreWebView2
            core.NavigationStarting += self._on_navigation_started
            core.NavigationCompleted += self._on_navigation_completed
            core.ProcessFailed += self._on_process_failed
            core.NewWindowRequested += self._on_new_window_requested

        def _on_navigation_started(self, _sender: Any, args: Any) -> None:
            self._navigation_started_signal.emit(str(args.Uri))

        def _on_navigation_completed(self, _sender: Any, args: Any) -> None:
            self._navigation_completed_signal.emit(
                bool(args.IsSuccess),
                "" if args.IsSuccess else str(args.WebErrorStatus),
            )

        def _on_process_failed(self, _sender: Any, args: Any) -> None:
            self._process_failed_signal.emit(str(args.ProcessFailedKind))

        def _on_new_window_requested(self, _sender: Any, args: Any) -> None:
            args.Handled = True
            self.widget.load_url(str(args.Uri))

        def _dom_loaded(self) -> None:
            self.state.load_progress = max(self.state.load_progress, 80)
            self._emit_state()

        def _navigation_started(self, url: str) -> None:
            self._load_started_at = time.perf_counter()
            self.state.current_url = url
            self.state.loading_state = LoadingState.LOADING
            self.state.load_progress = 0
            self.state.load_succeeded = None
            self.state.last_error = ""
            self.navigation_started.emit(url)
            self._emit_state()

        def _navigation_completed(self, succeeded: bool, error: str) -> None:
            self.state.load_succeeded = succeeded
            self.state.load_progress = 100
            self.state.load_duration_ms = (
                (time.perf_counter() - self._load_started_at) * 1000
                if self._load_started_at
                else 0.0
            )
            self.state.loading_state = LoadingState.LOADED if succeeded else LoadingState.FAILED
            self.state.last_error = "" if succeeded else f"WebView2 load failed: {error}"
            LOGGER.info(
                "WebView2 load finished success=%s url=%s duration=%.1fms",
                succeeded,
                self.state.current_url,
                self.state.load_duration_ms,
            )
            self._emit_state()

        def _process_failed(self, detail: str) -> None:
            self.state.loading_state = LoadingState.CRASHED
            self.state.render_process_termination = detail
            self.state.last_error = f"WebView2 process failed: {detail}"
            LOGGER.error(self.state.last_error)
            self.crashed.emit(self.state.last_error)
            self._emit_state()

        def load_url(self, url: str) -> None:
            self._load_started_at = time.perf_counter()
            self.state.current_url = url
            self.state.loading_state = LoadingState.LOADING
            self.state.load_progress = 0
            self.state.load_succeeded = None
            self.state.last_error = ""
            self._emit_state()
            self.widget.load_url(url)

        def reload(self) -> None:
            self.widget.reload()

        def go_back(self) -> None:
            if self.widget.is_ready and self.widget._webview.CanGoBack:
                self.widget._webview.GoBack()

        def go_forward(self) -> None:
            if self.widget.is_ready and self.widget._webview.CanGoForward:
                self.widget._webview.GoForward()

        def focus_game(self) -> None:
            self.widget.setFocus()
            if self.widget.is_ready:
                self.widget._webview.Focus()
            self.state.focus_state = True
            self._emit_state()

        def set_visible(self, visible: bool) -> None:
            self.widget.setVisible(visible)

        def stop(self) -> None:
            if self.widget.is_ready:
                self.widget._webview.CoreWebView2.Stop()
            self.state.loading_state = LoadingState.STOPPED
            self._emit_state()

        def shutdown(self) -> None:
            self.stop()
            self.widget.close()
            self.widget.deleteLater()

        def current_url(self) -> str:
            if self.widget.is_ready and self.widget._webview.Source:
                return str(self.widget._webview.Source)
            return self.state.current_url

        def engine_name(self) -> str:
            return "Microsoft WebView2"

    return WebView2Browser
