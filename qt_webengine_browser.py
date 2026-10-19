"""Persistent, genuinely embedded Qt WebEngine browser."""

import logging
import time
from pathlib import Path
from typing import Any

from .browser_base import BrowserState, LoadingState

LOGGER = logging.getLogger(__name__)


def qt_webengine_version() -> str:
    """Return the installed Qt WebEngine version without constructing a view."""
    try:
        from PySide6.QtCore import qVersion
        from PySide6.QtWebEngineCore import QWebEngineProfile

        del QWebEngineProfile
        return qVersion()
    except ImportError:
        return "unavailable"


def create_qt_webengine_browser_class() -> type:
    """Create the QObject implementation lazily for CLI-safe imports."""
    from PySide6.QtCore import QObject, QUrl, Signal
    from PySide6.QtWebEngineCore import (
        QWebEnginePage,
        QWebEngineProfile,
        QWebEngineSettings,
    )
    from PySide6.QtWebEngineWidgets import QWebEngineView

    class GameWebEngineView(QWebEngineView):
        """Keep reasonable popup navigation in the owned game view."""

        def createWindow(self, _window_type: Any) -> Any:
            return self

    class QtWebEngineBrowser(QObject):
        """Qt WebEngine adapter with persistent cache/cookies and state signals."""

        state_changed = Signal(object)
        fullscreen_requested = Signal(bool)
        crashed = Signal(str)

        def __init__(
            self,
            parent: Any,
            requested_mode: str,
            user_data_path: Path,
            allow_fullscreen: bool = True,
        ) -> None:
            super().__init__(parent)
            user_data_path.mkdir(parents=True, exist_ok=True)
            cache_path = user_data_path / "cache"
            cache_path.mkdir(parents=True, exist_ok=True)
            self.state = BrowserState(
                requested_mode=requested_mode,
                selected_engine="qt_webengine",
                loading_state=LoadingState.READY,
                supports_fullscreen=allow_fullscreen,
                supports_audio=True,
                supports_webgl=True,
                user_data_path=user_data_path,
            )
            self._load_started_at = 0.0
            self.profile = QWebEngineProfile("racing_controller", self)
            self.profile.setPersistentStoragePath(str(user_data_path / "storage"))
            self.profile.setCachePath(str(cache_path))
            self.profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
            self.profile.setPersistentCookiesPolicy(
                QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies
            )
            self.page = QWebEnginePage(self.profile, self)
            self.widget = GameWebEngineView(parent)
            self.widget.setPage(self.page)
            settings = self.widget.settings()
            for attribute, enabled in (
                (QWebEngineSettings.WebAttribute.JavascriptEnabled, True),
                (QWebEngineSettings.WebAttribute.LocalStorageEnabled, True),
                (QWebEngineSettings.WebAttribute.WebGLEnabled, True),
                (QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True),
                (QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture, True),
                (
                    QWebEngineSettings.WebAttribute.FullScreenSupportEnabled,
                    allow_fullscreen,
                ),
            ):
                settings.setAttribute(attribute, enabled)
            self.widget.loadStarted.connect(self._load_started)
            self.widget.loadProgress.connect(self._load_progress)
            self.widget.loadFinished.connect(self._load_finished)
            self.widget.urlChanged.connect(self._url_changed)
            self.widget.renderProcessTerminated.connect(self._render_process_terminated)
            self.page.fullScreenRequested.connect(self._full_screen_requested)
            self.page.certificateError.connect(self._certificate_error)

        def _emit_state(self) -> None:
            self.state_changed.emit(self.state)

        def _load_started(self) -> None:
            self._load_started_at = time.perf_counter()
            self.state.loading_state = LoadingState.LOADING
            self.state.load_progress = 0
            self.state.load_succeeded = None
            self.state.last_error = ""
            self._emit_state()

        def _load_progress(self, progress: int) -> None:
            self.state.load_progress = progress
            self._emit_state()

        def _load_finished(self, succeeded: bool) -> None:
            self.state.load_succeeded = succeeded
            self.state.load_duration_ms = (
                (time.perf_counter() - self._load_started_at) * 1000
                if self._load_started_at
                else 0.0
            )
            self.state.loading_state = LoadingState.LOADED if succeeded else LoadingState.FAILED
            if not succeeded:
                self.state.last_error = "The embedded page did not finish loading"
            LOGGER.info(
                "Qt WebEngine load finished success=%s url=%s duration=%.1fms",
                succeeded,
                self.state.current_url,
                self.state.load_duration_ms,
            )
            self._emit_state()

        def _url_changed(self, url: Any) -> None:
            self.state.current_url = url.toString()
            self._emit_state()

        def _render_process_terminated(self, status: Any, exit_code: int) -> None:
            detail = f"{status} (exit code {exit_code})"
            self.state.loading_state = LoadingState.CRASHED
            self.state.render_process_termination = detail
            self.state.last_error = f"Embedded browser renderer stopped: {detail}"
            LOGGER.error(self.state.last_error)
            self.crashed.emit(self.state.last_error)
            self._emit_state()

        def _full_screen_requested(self, request: Any) -> None:
            requested = bool(request.toggleOn())
            request.accept()
            self.fullscreen_requested.emit(requested)

        def _certificate_error(self, error: Any) -> None:
            description = str(error.description())
            LOGGER.error("Embedded browser certificate error: %s", description)
            error.rejectCertificate()
            self.state.loading_state = LoadingState.FAILED
            self.state.last_error = f"Certificate error: {description}"
            self._emit_state()

        def load_url(self, url: str) -> None:
            self.widget.load(QUrl(url))

        def reload(self) -> None:
            self.widget.reload()

        def go_back(self) -> None:
            self.widget.back()

        def go_forward(self) -> None:
            self.widget.forward()

        def focus_game(self) -> None:
            self.widget.setFocus()
            self.state.focus_state = True
            self._emit_state()

        def set_visible(self, visible: bool) -> None:
            self.widget.setVisible(visible)

        def stop(self) -> None:
            self.widget.stop()
            self.state.loading_state = LoadingState.STOPPED
            self._emit_state()

        def shutdown(self) -> None:
            self.widget.stop()
            self.widget.deleteLater()
            self.page.deleteLater()
            self.profile.deleteLater()
            self.state.loading_state = LoadingState.STOPPED

        def current_url(self) -> str:
            return self.widget.url().toString()

        def engine_name(self) -> str:
            return "Qt WebEngine"

    return QtWebEngineBrowser
