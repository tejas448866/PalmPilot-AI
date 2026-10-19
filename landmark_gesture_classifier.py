"""Rotation- and scale-invariant open-palm/fist classification."""

import math
from dataclasses import dataclass
from enum import Enum

from src.hand_tracking import DetectedHand, Point2D
from src.utils.geometry import distance

FINGER_CHAINS = {
    "thumb": (1, 2, 3, 4),
    "index": (5, 6, 7, 8),
    "middle": (9, 10, 11, 12),
    "ring": (13, 14, 15, 16),
    "pinky": (17, 18, 19, 20),
}
PALM_INDICES = (0, 5, 9, 13, 17)


class DeterministicGesture(str, Enum):
    """Clear basic landmark classes."""

    OPEN_PALM = "open_palm"
    CLOSED_FIST = "closed_fist"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class LandmarkGestureConfig:
    """Practical normalized thresholds for basic gestures."""

    extension_angle_degrees: float = 115.0
    fold_angle_degrees: float = 95.0
    extended_tip_distance: float = 0.90
    folded_tip_distance: float = 0.75
    open_openness_threshold: float = 0.85
    closed_openness_threshold: float = 0.80
    open_extended_fingers: int = 3
    closed_folded_fingers: int = 3
    open_max_folded_fingers: int = 1
    closed_max_extended_fingers: int = 1
    open_exit_extended_fingers: int = 3
    closed_exit_folded_fingers: int = 3
    open_exit_openness_threshold: float = 0.82
    closed_exit_openness_threshold: float = 0.90


@dataclass(frozen=True)
class LandmarkGestureResult:
    """Classification plus interpretable measurements for diagnostics."""

    gesture: DeterministicGesture
    finger_states: tuple[str, ...]
    openness_score: float
    extended_count: int
    folded_count: int
    reason: str
    supporting_gesture: str | None = None


def _joint_angle(a: Point2D, b: Point2D, c: Point2D) -> float:
    first = (a.x - b.x, a.y - b.y)
    second = (c.x - b.x, c.y - b.y)
    denominator = math.hypot(*first) * math.hypot(*second)
    if denominator <= 1e-9:
        return 0.0
    cosine = max(
        -1.0,
        min(
            1.0,
            (first[0] * second[0] + first[1] * second[1]) / denominator,
        ),
    )
    return math.degrees(math.acos(cosine))


class LandmarkGestureClassifier:
    """Classify broad open/folded geometry without camera-axis comparisons."""

    def __init__(self, config: LandmarkGestureConfig | None = None) -> None:
        self.config = config or LandmarkGestureConfig()

    def classify(self, hand: DetectedHand) -> LandmarkGestureResult:
        """Return a tolerant open/fist/ambiguous classification."""
        points = hand.landmarks.normalized
        if len(points) != 21:
            raise ValueError(f"Expected 21 landmarks, received {len(points)}")
        palm_center = Point2D(
            sum(points[index].x for index in PALM_INDICES) / len(PALM_INDICES),
            sum(points[index].y for index in PALM_INDICES) / len(PALM_INDICES),
        )
        palm_size = max(
            distance(points[0], points[9]),
            distance(points[5], points[17]),
            1e-6,
        )
        states: list[str] = []
        normalized_tip_distances: list[float] = []
        for name, chain in FINGER_CHAINS.items():
            first_angle = _joint_angle(points[chain[0]], points[chain[1]], points[chain[2]])
            second_angle = _joint_angle(points[chain[1]], points[chain[2]], points[chain[3]])
            average_angle = (first_angle + second_angle) / 2.0
            tip_distance = distance(points[chain[3]], palm_center) / palm_size
            normalized_tip_distances.append(tip_distance)
            extension_distance = self.config.extended_tip_distance
            fold_distance = self.config.folded_tip_distance
            if name == "thumb":
                extension_distance *= 0.82
                fold_distance *= 0.90
            if (
                average_angle >= self.config.extension_angle_degrees
                and tip_distance >= extension_distance
            ):
                states.append("extended")
            elif average_angle <= self.config.fold_angle_degrees or tip_distance <= fold_distance:
                states.append("folded")
            else:
                states.append("uncertain")
        extended = states.count("extended")
        folded = states.count("folded")
        openness = sum(normalized_tip_distances) / len(normalized_tip_distances)
        if (
            extended >= self.config.open_extended_fingers
            and folded <= self.config.open_max_folded_fingers
            and openness >= self.config.open_openness_threshold
        ):
            gesture = DeterministicGesture.OPEN_PALM
            reason = f"{extended} extended fingers; openness {openness:.2f}"
        elif (
            folded >= self.config.closed_folded_fingers
            and extended <= self.config.closed_max_extended_fingers
            and openness <= self.config.closed_openness_threshold
        ):
            gesture = DeterministicGesture.CLOSED_FIST
            reason = f"{folded} folded fingers; openness {openness:.2f}"
        else:
            gesture = DeterministicGesture.AMBIGUOUS
            reason = (
                f"insufficient consensus: extended={extended}, folded={folded}, "
                f"openness={openness:.2f}"
            )
        supporting_gesture = None
        if (
            extended >= self.config.open_exit_extended_fingers
            and openness >= self.config.open_exit_openness_threshold
        ):
            supporting_gesture = DeterministicGesture.OPEN_PALM.value
        elif (
            folded >= self.config.closed_exit_folded_fingers
            and openness <= self.config.closed_exit_openness_threshold
        ):
            supporting_gesture = DeterministicGesture.CLOSED_FIST.value
        return LandmarkGestureResult(
            gesture,
            tuple(states),
            openness,
            extended,
            folded,
            reason,
            supporting_gesture,
        )
