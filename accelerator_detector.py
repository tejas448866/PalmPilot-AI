"""Vertical-region accelerator detection."""

from src.hand_tracking import HandTrackingResult
from src.utils.constants import MIDDLE_MCP


class AcceleratorDetector:
    """Activate when both hand reference points are above a threshold."""

    def __init__(self, threshold_y: float = 0.38) -> None:
        self.threshold_y = threshold_y

    def detect(self, result: HandTrackingResult) -> bool:
        """Return whether both hands request acceleration."""
        return len(result.hands) >= 2 and all(
            hand.landmarks.point(MIDDLE_MCP).y < self.threshold_y for hand in result.hands[:2]
        )
