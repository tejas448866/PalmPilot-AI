"""Optional landmark-based auxiliary gestures."""

from src.hand_tracking import DetectedHand, HandTrackingResult
from src.utils.constants import INDEX_TIP, MIDDLE_TIP, PINKY_TIP, THUMB_TIP, WRIST
from src.utils.geometry import distance

from .gesture_state import Command


class AuxiliaryGestureDetector:
    """Detect opt-in pinch/open-hand gestures with configurable thresholds."""

    def __init__(
        self,
        enabled: dict[str, bool] | None = None,
        pinch_distance: float = 0.055,
        open_hand_distance: float = 0.22,
    ) -> None:
        self.enabled = enabled or {}
        self.pinch_distance = pinch_distance
        self.open_hand_distance = open_hand_distance

    def detect(self, result: HandTrackingResult) -> set[Command]:
        """Return simultaneous auxiliary commands; disabled actions never fire."""
        commands: set[Command] = set()
        hands = result.hands[:2]
        if not hands:
            return commands
        left = min(hands, key=lambda hand: hand.landmarks.point(WRIST).x)
        right = max(hands, key=lambda hand: hand.landmarks.point(WRIST).x)
        if self.enabled.get("nitro") and self._pinched(left):
            commands.add(Command.NITRO)
        if self.enabled.get("horn") and self._pinched(right):
            commands.add(Command.HORN)
        if (
            self.enabled.get("pause")
            and len(hands) == 2
            and all(self._pinched(hand) for hand in hands)
        ):
            commands.add(Command.PAUSE)
        if (
            self.enabled.get("reset_calibration")
            and len(hands) == 2
            and all(self._open(hand) for hand in hands)
        ):
            commands.add(Command.RESET_CALIBRATION)
        return commands

    def _pinched(self, hand: DetectedHand) -> bool:
        return (
            distance(hand.landmarks.point(THUMB_TIP), hand.landmarks.point(INDEX_TIP))
            <= self.pinch_distance
        )

    def _open(self, hand: DetectedHand) -> bool:
        wrist = hand.landmarks.point(WRIST)
        return all(
            distance(wrist, hand.landmarks.point(index)) >= self.open_hand_distance
            for index in (INDEX_TIP, MIDDLE_TIP, PINKY_TIP)
        )
