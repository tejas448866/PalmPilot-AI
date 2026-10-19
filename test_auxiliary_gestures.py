"""Optional gestures remain disabled by default."""

from src.gesture.auxiliary_gesture_detector import AuxiliaryGestureDetector
from tests.fixtures.sample_landmarks import make_two_hands


def test_auxiliary_gestures_disabled_by_default() -> None:
    assert AuxiliaryGestureDetector().detect(make_two_hands()) == set()
