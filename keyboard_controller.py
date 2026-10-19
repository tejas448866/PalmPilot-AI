"""Exception-safe pynput keyboard adapter."""

import logging
from collections.abc import Callable
from typing import Any

from .key_mapping import resolve_key, validate_key_name

LOGGER = logging.getLogger(__name__)


class KeyboardController:
    """Track active keys and avoid duplicate input events."""

    def __init__(
        self,
        dry_run: bool = True,
        backend: Any | None = None,
        resolver: Callable[[str], Any] = resolve_key,
    ) -> None:
        self.dry_run = dry_run
        if backend is None and not dry_run:
            from pynput.keyboard import Controller

            backend = Controller()
        if not dry_run and backend is None:
            raise RuntimeError("A keyboard backend is required in live mode")
        self.backend = backend
        self.resolver = resolver
        self.active_keys: set[str] = set()

    def press(self, name: str) -> None:
        """Press a key once if it is not already active."""
        normalized = validate_key_name(name)
        if normalized in self.active_keys:
            return
        if not self.dry_run:
            assert self.backend is not None
            self.backend.press(self.resolver(normalized))
        LOGGER.info("%s press %s", "DRY-RUN" if self.dry_run else "Keyboard", normalized)
        self.active_keys.add(normalized)

    def release(self, name: str) -> None:
        """Release a key only if it is tracked active."""
        normalized = validate_key_name(name)
        if normalized not in self.active_keys:
            return
        try:
            if not self.dry_run:
                assert self.backend is not None
                self.backend.release(self.resolver(normalized))
        finally:
            self.active_keys.discard(normalized)
            LOGGER.info("%s release %s", "DRY-RUN" if self.dry_run else "Keyboard", normalized)

    def set_active(self, names: set[str]) -> None:
        """Apply an exact desired active-key set, releasing first."""
        normalized = {validate_key_name(name) for name in names}
        for name in sorted(self.active_keys - normalized):
            self.release(name)
        for name in sorted(normalized - self.active_keys):
            self.press(name)

    def release_all(self) -> None:
        """Best-effort release of every tracked key."""
        for name in list(self.active_keys):
            try:
                self.release(name)
            except Exception:
                LOGGER.exception("Failed to release key %s", name)
                self.active_keys.discard(name)

    def __enter__(self) -> "KeyboardController":
        return self

    def __exit__(self, *_: object) -> None:
        self.release_all()
