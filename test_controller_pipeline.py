"""Abstract command to mocked keyboard behavior."""

from unittest.mock import Mock

from src.controller import CommandManager, KeyboardController
from src.gesture import Command

MAPPING = {"accelerate": "up", "brake": "down", "left": "left", "right": "right"}


def test_command_switch_loss_and_shutdown_release() -> None:
    backend = Mock()
    keyboard = KeyboardController(False, backend=backend, resolver=lambda name: name)
    manager = CommandManager(keyboard, MAPPING, lost_tracking_timeout=0.1)
    manager.apply(Command.LEFT, Command.ACCELERATE, True, now=1.0)
    assert keyboard.active_keys == {"left", "up"}
    manager.apply(Command.RIGHT, Command.BRAKE, True, now=1.1)
    assert keyboard.active_keys == {"right", "down"}
    manager.apply(Command.RIGHT, Command.BRAKE, False, now=1.25)
    assert keyboard.active_keys == set()
    manager.shutdown()
    assert backend.release.call_count == 4


def test_dry_run_never_calls_backend() -> None:
    backend = Mock()
    keyboard = KeyboardController(True, backend=backend)
    CommandManager(keyboard, MAPPING).apply(Command.LEFT, Command.ACCELERATE, True)
    backend.press.assert_not_called()
