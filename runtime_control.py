"""Translate ML mappings into the existing abstract controller state."""

from dataclasses import dataclass

from src.gesture import Command


@dataclass(frozen=True)
class MappedGestureActions:
    """Conflict-safe commands produced by one stable gesture."""

    pedal: Command = Command.IDLE
    steering: Command | None = None
    auxiliary: frozenset[Command] = frozenset()


def resolve_mapped_actions(commands: set[Command]) -> MappedGestureActions:
    """Resolve mappings without creating a separate keyboard dispatcher."""
    if Command.ACCELERATE in commands and commands & {Command.BRAKE, Command.REVERSE}:
        raise ValueError("A gesture cannot map to accelerator and brake simultaneously")
    pedal = Command.IDLE
    if Command.ACCELERATE in commands:
        pedal = Command.ACCELERATE
    elif commands & {Command.BRAKE, Command.REVERSE}:
        pedal = Command.BRAKE
    steering = (
        Command.LEFT
        if Command.LEFT in commands
        else Command.RIGHT if Command.RIGHT in commands else None
    )
    consumed = {
        Command.ACCELERATE,
        Command.BRAKE,
        Command.REVERSE,
        Command.LEFT,
        Command.RIGHT,
        Command.STRAIGHT,
        Command.IDLE,
    }
    return MappedGestureActions(pedal, steering, frozenset(commands - consumed))


def select_pedal_command(ml_active: bool, ml_pedal: Command, rule_based_pedal: Command) -> Command:
    """Make recognizer precedence explicit: ML replaces rules when active."""
    return ml_pedal if ml_active else rule_based_pedal
