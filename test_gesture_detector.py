"""Vertical-region pedal gesture tests."""

from src.gesture import Command
from src.gesture.accelerator_detector import AcceleratorDetector
from src.gesture.brake_detector import BrakeDetector
from src.gesture.gesture_detector import GestureDetector
from src.hand_tracking import HandTrackingResult
from tests.fixtures.sample_landmarks import make_two_hands


def test_accelerate_brake_and_idle() -> None:
    detector = GestureDetector(AcceleratorDetector(0.4), BrakeDetector(0.65))
    assert detector.detect_pedal(make_two_hands(0.2, 0.2)) is Command.ACCELERATE
    assert detector.detect_pedal(make_two_hands(0.8, 0.8)) is Command.BRAKE
    assert detector.detect_pedal(make_two_hands()) is Command.IDLE
    assert detector.detect_pedal(HandTrackingResult()) is Command.IDLE


def test_conflict_resolves_idle() -> None:
    detector = GestureDetector(AcceleratorDetector(0.8), BrakeDetector(0.2))
    assert detector.detect_pedal(make_two_hands()) is Command.IDLE
