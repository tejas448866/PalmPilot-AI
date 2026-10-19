"""Thread-safe in-process runtime configuration updates."""

from collections.abc import Callable
from threading import RLock
from typing import Any


class RuntimeSettings:
    """Publish settings changes to a running controller without restart."""

    def __init__(self, initial: dict[str, Any] | None = None) -> None:
        self._values = dict(initial or {})
        self._changes: dict[str, Any] = {}
        self._subscribers: list[Callable[[str, Any], None]] = []
        self._lock = RLock()

    def set(self, key: str, value: Any) -> None:
        """Atomically update a dotted setting and notify subscribers."""
        with self._lock:
            self._values[key] = value
            self._changes[key] = value
            subscribers = tuple(self._subscribers)
        for subscriber in subscribers:
            subscriber(key, value)

    def get(self, key: str, default: Any = None) -> Any:
        """Read one value."""
        with self._lock:
            return self._values.get(key, default)

    def consume_changes(self) -> dict[str, Any]:
        """Return and clear pending changes."""
        with self._lock:
            changes = dict(self._changes)
            self._changes.clear()
            return changes

    def subscribe(self, callback: Callable[[str, Any], None]) -> None:
        """Register a synchronous lightweight change callback."""
        with self._lock:
            self._subscribers.append(callback)
