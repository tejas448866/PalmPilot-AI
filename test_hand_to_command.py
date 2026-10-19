"""Synthetic landmarks through steering and gesture logic."""

from src.gesture import Command
from src.gesture.accelerator_detector import AcceleratorDetector
from src.gesture.brake_detector import BrakeDetector
from src.gesture.gesture_detector import GestureDetector
from src.gesture.steering_detector import SteeringDetector
from src.hand_tracking import HandRoleTracker
from tests.fixtures.sample_landmarks import make_two_hands


def test_landmarks_to_combined_commands() -> None:
    hands = make_two_hands(0.2, 0.2)
    steering = SteeringDetector().detect(HandRoleTracker().update(hands))
    pedal = GestureDetector(AcceleratorDetector(0.4), BrakeDetector(0.7)).detect_pedal(hands)
    assert steering.command is Command.STRAIGHT
    assert pedal is Command.ACCELERATE
