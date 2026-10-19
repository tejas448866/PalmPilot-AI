"""Compose independent pedal detectors."""

from src.hand_tracking import HandTrackingResult

from .accelerator_detector import AcceleratorDetector
from .brake_detector import BrakeDetector
from .gesture_state import Command


class GestureDetector:
    """Resolve accelerator/brake gestures into one pedal command."""

    def __init__(self, accelerator: AcceleratorDetector, brake: BrakeDetector) -> None:
        self.accelerator = accelerator
        self.brake = brake

    def detect_pedal(self, result: HandTrackingResult) -> Command:
        """Return a conflict-safe pedal command."""
        acceleration = self.accelerator.detect(result)
        braking = self.brake.detect(result)
        if acceleration == braking:
            return Command.IDLE
        return Command.ACCELERATE if acceleration else Command.BRAKE
