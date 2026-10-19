"""Engine-neutral browser state and interface."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Protocol


class LoadingState(str, Enum):
    """Observable embedded-browser lifecycle."""

    NOT_INITIALIZED = "not_initialized"
    READY = "ready"
    LOADING = "loading"
    LOADED = "loaded"
    FAILED = "failed"
    CRASHED = "crashed"
    STOPPED = "stopped"


@dataclass
class BrowserState:
    """Diagnostics shared by all browser engines."""

    requested_mode: str
    selected_engine: str
    loading_state: LoadingState = LoadingState.NOT_INITIALIZED
    current_url: str = ""
    load_progress: int = 0
    initialization_succeeded: bool | None = None
    load_succeeded: bool | None = None
    load_duration_ms: float = 0.0
    last_error: str = ""
    render_process_termination: str = ""
    focus_state: bool = False
    supports_fullscreen: bool = False
    supports_audio: bool = False
    supports_webgl: bool = False
    user_data_path: Path | None = None
    fallback_reason: str = ""

    def diagnostics(self) -> dict[str, Any]:
        """Return a JSON-safe diagnostics mapping."""
        return {
            "requested_integration_mode": self.requested_mode,
            "selected_browser_engine": self.selected_engine,
            "embedded_loading_state": self.loading_state.value,
            "page_url": self.current_url,
            "load_progress": self.load_progress,
            "embedded_initialization_result": self.initialization_succeeded,
            "load_success": self.load_succeeded,
            "load_duration_ms": round(self.load_duration_ms, 1),
            "webgl_capability": self.supports_webgl,
            "audio_supported": self.supports_audio,
            "fullscreen_supported": self.supports_fullscreen,
            "render_process_termination": self.render_process_termination,
            "browser_user_data_path": str(self.user_data_path or ""),
            "external_fallback_reason": self.fallback_reason,
            "last_browser_error": self.last_error,
            "game_focus_state": self.focus_state,
        }


class EmbeddedBrowser(Protocol):
    """Operations consumed by the desktop workspace."""

    widget: Any
    state: BrowserState
    state_changed: Any
    navigation_started: Any
    fullscreen_requested: Any
    crashed: Any

    def load_url(self, url: str) -> None: ...

    def reload(self) -> None: ...

    def go_back(self) -> None: ...

    def go_forward(self) -> None: ...

    def focus_game(self) -> None: ...

    def set_visible(self, visible: bool) -> None: ...

    def stop(self) -> None: ...

    def shutdown(self) -> None: ...

    def current_url(self) -> str: ...

    def engine_name(self) -> str: ...
