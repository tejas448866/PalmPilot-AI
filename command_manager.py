"""Resolve abstract commands and tracking loss to desired keys."""

import time

from src.gesture import Command

from .keyboard_controller import KeyboardController


class CommandManager:
    """Translate conflict-safe logical state into keyboard state."""

    def __init__(
        self,
        keyboard: KeyboardController,
        mapping: dict[str, str],
        lost_tracking_timeout: float = 0.35,
    ) -> None:
        self.keyboard = keyboard
        self.mapping = mapping
        self.timeout = lost_tracking_timeout
        self.last_tracking_time = time.monotonic()

    def apply(
        self,
        steering: Command,
        pedal: Command,
        tracking_visible: bool,
        now: float | None = None,
        auxiliary: set[Command] | None = None,
    ) -> None:
        """Apply one frame of commands and release after tracking timeout."""
        current_time = now if now is not None else time.monotonic()
        if tracking_visible:
            self.last_tracking_time = current_time
        elif current_time - self.last_tracking_time >= self.timeout:
            self.keyboard.release_all()
            return
        desired: set[str] = set()
        if steering is Command.LEFT:
            desired.add(self.mapping["left"])
        elif steering is Command.RIGHT:
            desired.add(self.mapping["right"])
        if pedal is Command.ACCELERATE:
            desired.add(self.mapping["accelerate"])
        elif pedal in (Command.BRAKE, Command.REVERSE):
            desired.add(self.mapping["brake"])
        for command in auxiliary or set():
            key = self.mapping.get(command.value)
            if key:
                desired.add(key)
        self.keyboard.set_active(desired)

    def shutdown(self) -> None:
        """Release all controller state."""
        self.keyboard.release_all()
