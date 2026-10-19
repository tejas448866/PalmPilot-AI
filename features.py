"""Fixed-length, translation/scale/rotation-normalized hand features."""

import math
from dataclasses import dataclass

from src.hand_tracking import DetectedHand, Point2D
from src.utils.constants import (
    FINGERTIPS,
    INDEX_MCP,
    MIDDLE_MCP,
    PINKY_MCP,
    WRIST,
)
from src.utils.geometry import distance

FINGER_CHAINS = ((1, 2, 3, 4), (5, 6, 7, 8), (9, 10, 11, 12), (13, 14, 15, 16), (17, 18, 19, 20))


def _angle(a: Point2D, b: Point2D, c: Point2D) -> float:
    ab, cb = (a.x - b.x, a.y - b.y), (c.x - b.x, c.y - b.y)
    denominator = math.hypot(*ab) * math.hypot(*cb)
    if denominator <= 1e-9:
        return 0.0
    cosine = max(-1.0, min(1.0, (ab[0] * cb[0] + ab[1] * cb[1]) / denominator))
    return math.acos(cosine) / math.pi


@dataclass(frozen=True)
class FeatureVector:
    """Model-ready features and schema name."""

    values: tuple[float, ...]
    schema: str = "hand_features_v1"


class HandFeatureExtractor:
    """Extract geometric features invariant to position, scale, and in-plane rotation."""

    schema = "hand_features_v1"

    def extract(self, hand: DetectedHand) -> FeatureVector:
        """Create one deterministic fixed-length feature vector."""
        points = hand.landmarks.normalized
        if len(points) != 21:
            raise ValueError(f"Expected 21 landmarks, received {len(points)}")
        wrist = points[WRIST]
        axis = points[MIDDLE_MCP]
        rotation = math.atan2(axis.y - wrist.y, axis.x - wrist.x)
        cosine, sine = math.cos(-rotation), math.sin(-rotation)
        scale = max(
            distance(wrist, points[MIDDLE_MCP]),
            distance(points[INDEX_MCP], points[PINKY_MCP]),
            1e-6,
        )
        coordinates: list[float] = []
        for point in points:
            x, y = (point.x - wrist.x) / scale, (point.y - wrist.y) / scale
            coordinates.extend((x * cosine - y * sine, x * sine + y * cosine))
        angles = [
            _angle(points[chain[0]], points[chain[1]], points[chain[2]]) for chain in FINGER_CHAINS
        ]
        angles.extend(
            _angle(points[chain[1]], points[chain[2]], points[chain[3]]) for chain in FINGER_CHAINS
        )
        tip_distances = [
            min(2.0, distance(points[first], points[second]) / scale) / 2.0
            for index, first in enumerate(FINGERTIPS)
            for second in FINGERTIPS[index + 1 :]
        ]
        finger_states = [
            float(distance(wrist, points[chain[3]]) > distance(wrist, points[chain[1]]) * 1.25)
            for chain in FINGER_CHAINS
        ]
        openness = sum(distance(wrist, points[index]) for index in FINGERTIPS) / (5 * scale)
        palm_orientation = (
            math.atan2(
                points[PINKY_MCP].y - points[INDEX_MCP].y,
                points[PINKY_MCP].x - points[INDEX_MCP].x,
            )
            / math.pi
        )
        wrist_orientation = rotation / math.pi
        values = coordinates + angles + tip_distances + finger_states
        values.extend((max(0.0, min(2.0, openness)) / 2.0, palm_orientation, wrist_orientation))
        if not all(math.isfinite(value) for value in values):
            raise ValueError("Feature extraction produced non-finite values")
        return FeatureVector(tuple(values), self.schema)

    @property
    def feature_count(self) -> int:
        """Return the stable model input width."""
        return 70
