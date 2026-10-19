"""Abstract commands and per-frame gesture state."""

from dataclasses import dataclass
from enum import Enum


class Command(str, Enum):
    """Safe logical controller commands."""

    LEFT = "left"
    RIGHT = "right"
    STRAIGHT = "straight"
    ACCELERATE = "accelerate"
    BRAKE = "brake"
    REVERSE = "reverse"
    IDLE = "idle"
    EXIT = "exit"
    NITRO = "nitro"
    HORN = "horn"
    PAUSE = "pause"
    RESET_CALIBRATION = "reset_calibration"


@dataclass(frozen=True)
class GestureState:
    """Combined steering and pedal decision."""

    steering: Command = Command.STRAIGHT
    pedal: Command = Command.IDLE
    raw_angle: float | None = None
    smoothed_angle: float | None = None
