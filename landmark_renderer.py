"""Resolution-aware role-colored hand landmark rendering."""

from dataclasses import dataclass
from typing import Any

from src.hand_tracking import HandTrackingResult, SteeringHands

CONNECTIONS = (
    (0, 1),
    (1, 2),
    (2, 3),
    (3, 4),
    (0, 5),
    (5, 6),
    (6, 7),
    (7, 8),
    (5, 9),
    (9, 10),
    (10, 11),
    (11, 12),
    (9, 13),
    (13, 14),
    (14, 15),
    (15, 16),
    (13, 17),
    (17, 18),
    (18, 19),
    (19, 20),
    (0, 17),
)
PALM_JOINTS = {0, 5, 9, 13, 17}


@dataclass(frozen=True)
class LandmarkStyle:
    """Configurable landmark dimensions at 720p baseline."""

    landmark_radius: int = 5
    palm_landmark_radius: int = 7
    connection_thickness: int = 2
    ui_scale: float = 1.0


def draw_landmarks(
    frame: Any,
    result: HandTrackingResult,
    roles: SteeringHands | None = None,
    style: LandmarkStyle | None = None,
) -> None:
    """Draw clean connections and distinguish spatial steering roles."""
    import cv2

    style = style or LandmarkStyle()
    height = int(frame.shape[0])
    scale = max(0.65, height / 720.0) * style.ui_scale
    role_by_id: dict[int, tuple[str, bool]] = {}
    if roles:
        for tracked in (roles.steering_left, roles.steering_right):
            if tracked and not tracked.stale:
                role_by_id[id(tracked.detected_hand)] = (tracked.role, tracked.stale)
    colors = {
        "steering_left": (255, 170, 40),
        "steering_right": (80, 210, 255),
        "unknown": (110, 230, 130),
    }
    for hand in result.hands:
        role, stale = role_by_id.get(id(hand), ("unknown", False))
        color = colors[role]
        if stale:
            color = (
                int(color[0] * 0.5),
                int(color[1] * 0.5),
                int(color[2] * 0.5),
            )
        pixels = hand.landmarks.pixels
        thickness = max(1, round(style.connection_thickness * scale))
        for start, end in CONNECTIONS:
            a, b = pixels[start], pixels[end]
            cv2.line(
                frame,
                (round(a.x), round(a.y)),
                (round(b.x), round(b.y)),
                color,
                thickness,
                cv2.LINE_AA,
            )
        for index, point in enumerate(pixels):
            base = style.palm_landmark_radius if index in PALM_JOINTS else style.landmark_radius
            radius = max(2, round(base * scale))
            center = (round(point.x), round(point.y))
            cv2.circle(frame, center, radius + 2, (18, 18, 18), -1, cv2.LINE_AA)
            cv2.circle(frame, center, radius, color, -1, cv2.LINE_AA)
