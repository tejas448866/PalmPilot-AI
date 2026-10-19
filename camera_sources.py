"""Privacy-first camera discovery, persistence, switching, and failover."""

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.exceptions import CameraError, CameraNotAvailableError

from .camera_manager import CameraManager

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class CameraCapabilities:
    """Capabilities reported by an opened OpenCV source."""

    width: int
    height: int
    fps: float
    backend: str


@dataclass(frozen=True)
class CameraSource:
    """Local or explicitly configured camera source."""

    source_id: str
    name: str
    kind: str
    capture_source: int | str
    enabled: bool = True
    backend_order: list[str] = field(default_factory=lambda: ["dshow", "msmf", "default"])


class CameraRegistry:
    """Enumerate local cameras and parse opt-in virtual/network sources."""

    def __init__(self, state_path: Path = Path("data/camera_state.json")) -> None:
        self.state_path = state_path

    def enumerate_local(self, maximum_index: int = 6) -> list[CameraSource]:
        """Probe likely local indices without retaining handles."""
        import cv2

        sources: list[CameraSource] = []
        previous = cv2.getLogLevel() if hasattr(cv2, "getLogLevel") else None
        try:
            if hasattr(cv2, "setLogLevel"):
                cv2.setLogLevel(2)
            for index in range(maximum_index + 1):
                capture = cv2.VideoCapture(index, cv2.CAP_DSHOW)
                if capture.isOpened():
                    backend_name = (
                        capture.getBackendName() if hasattr(capture, "getBackendName") else ""
                    )
                    kind = "obs" if "obs" in backend_name.lower() else "local"
                    sources.append(CameraSource(f"camera-{index}", f"Camera {index}", kind, index))
                capture.release()
        finally:
            if previous is not None:
                cv2.setLogLevel(previous)
        return sources

    def configured(self, entries: list[dict[str, Any]]) -> list[CameraSource]:
        """Parse configuration without performing network discovery or calls."""
        sources: list[CameraSource] = []
        for entry in entries:
            enabled = bool(entry.get("enabled", False))
            source = entry.get("source")
            if not enabled:
                continue
            kind = str(entry.get("kind", "local")).lower()
            if kind not in {"local", "obs", "droidcam", "ip_webcam"}:
                raise ValueError(f"Unsupported camera source kind: {kind}")
            capture_source: int | str
            if kind in {"local", "obs"}:
                capture_source = self._camera_index(source)
            else:
                if not isinstance(source, str) or not source.strip():
                    raise ValueError(
                        f"Camera source {entry.get('id', '<unknown>')!r} "
                        "requires a non-empty stream URL"
                    )
                capture_source = source
            sources.append(
                CameraSource(
                    str(entry["id"]),
                    str(entry.get("name", entry["id"])),
                    kind,
                    capture_source,
                    True,
                    list(entry.get("backend_order", ["dshow", "msmf", "default"])),
                )
            )
        return sources

    @staticmethod
    def _camera_index(value: object) -> int:
        """Validate and normalize a local or virtual camera index."""
        if isinstance(value, bool):
            raise ValueError("Camera index must be a non-negative integer, not bool")
        if isinstance(value, int):
            index = value
        elif isinstance(value, str):
            normalized = value.strip()
            if not normalized.isdecimal():
                raise ValueError(f"Camera index must be a non-negative integer; got {value!r}")
            index = int(normalized)
        elif value is None:
            raise ValueError("Camera index is required for local and OBS camera sources")
        else:
            raise ValueError(
                "Camera index must be an integer or numeric string; " f"got {type(value).__name__}"
            )
        if index < 0:
            raise ValueError(f"Camera index must be non-negative; got {index}")
        return index

    def detect_capabilities(
        self, source: CameraSource, manager_factory: Callable[[CameraSource], CameraManager]
    ) -> CameraCapabilities:
        """Open one source briefly and report accepted mode/backend."""
        manager = manager_factory(source)
        try:
            actual = manager.diagnostics.actual_resolution
            return CameraCapabilities(
                actual[0],
                actual[1],
                manager.actual_fps,
                manager.diagnostics.backend,
            )
        finally:
            manager.release()

    def remember(self, source_id: str) -> None:
        """Persist only the selected source identifier locally."""
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps({"last_source_id": source_id}), encoding="utf-8")

    def last_source_id(self) -> str | None:
        """Load the last selected camera identifier."""
        try:
            return str(json.loads(self.state_path.read_text(encoding="utf-8"))["last_source_id"])
        except (FileNotFoundError, KeyError, json.JSONDecodeError):
            return None


class MultiCameraManager:
    """Proxy CameraManager with hot switching and bounded reconnect/failover."""

    def __init__(
        self,
        sources: list[CameraSource],
        manager_factory: Callable[[CameraSource], CameraManager],
        registry: CameraRegistry | None = None,
        preferred_source_id: str | None = None,
        reconnect_attempts: int = 2,
    ) -> None:
        if not sources:
            raise CameraNotAvailableError("No enabled camera sources are configured")
        self.sources = sources
        self.manager_factory = manager_factory
        self.registry = registry or CameraRegistry()
        self.reconnect_attempts = reconnect_attempts
        remembered = preferred_source_id or self.registry.last_source_id()
        self.index = next(
            (i for i, source in enumerate(sources) if source.source_id == remembered), 0
        )
        self.manager = self._open_from(self.index)

    @property
    def diagnostics(self) -> Any:
        """Expose current CameraManager diagnostics."""
        return self.manager.diagnostics

    @property
    def current_source(self) -> CameraSource:
        """Return current source metadata."""
        return self.sources[self.index]

    def read(self) -> Any:
        """Read, reconnect current source, then fail over if necessary."""
        try:
            return self.manager.read()
        except CameraError:
            LOGGER.warning("Camera source %s disconnected", self.current_source.source_id)
        for _ in range(self.reconnect_attempts):
            try:
                self.manager.release()
                self.manager = self.manager_factory(self.current_source)
                return self.manager.read()
            except CameraError:
                continue
        for offset in range(1, len(self.sources)):
            try:
                self.switch_to((self.index + offset) % len(self.sources))
                return self.manager.read()
            except CameraError:
                continue
        raise CameraError("All camera reconnect and failover attempts failed")

    def switch_to(self, source: int | str) -> CameraSource:
        """Hot-switch by list index or stable identifier."""
        target = (
            source
            if isinstance(source, int)
            else next(
                (i for i, item in enumerate(self.sources) if item.source_id == source),
                -1,
            )
        )
        if not 0 <= target < len(self.sources):
            raise CameraNotAvailableError(f"Unknown camera source: {source}")
        new_manager = self._open_from(target)
        old = self.manager
        self.manager = new_manager
        self.index = target
        old.release()
        return self.current_source

    def switch_next(self) -> CameraSource:
        """Switch to the next configured source."""
        return self.switch_to((self.index + 1) % len(self.sources))

    def _open_from(self, index: int) -> CameraManager:
        manager = self.manager_factory(self.sources[index])
        self.registry.remember(self.sources[index].source_id)
        return manager

    def release(self) -> None:
        """Release the current camera."""
        self.manager.release()
