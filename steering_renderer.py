"""Polished virtual steering-wheel HUD."""

import math
from typing import Any

from src.gesture.steering_detector import SteeringResult
from src.hand_tracking import SteeringHands


def _dashed_line(
    frame: Any,
    start: tuple[int, int],
    end: tuple[int, int],
    color: tuple[int, int, int],
    thickness: int,
) -> None:
    import cv2

    length = max(1.0, math.dist(start, end))
    for offset in range(0, round(length), 18):
        end_offset = min(offset + 10, length)
        a = (
            round(start[0] + (end[0] - start[0]) * offset / length),
            round(start[1] + (end[1] - start[1]) * offset / length),
        )
        b = (
            round(start[0] + (end[0] - start[0]) * end_offset / length),
            round(start[1] + (end[1] - start[1]) * end_offset / length),
        )
        cv2.line(frame, a, b, color, thickness, cv2.LINE_AA)


def draw_steering(
    frame: Any,
    steering: SteeringResult,
    roles: SteeringHands | None = None,
    line_thickness: int = 5,
    ui_scale: float = 1.0,
    show_wheel_circle: bool = True,
) -> None:
    """Draw valid wheel geometry; stale geometry is faded and dashed."""
    import cv2

    if not steering.valid or steering.left_point is None or steering.right_point is None:
        return
    height, width = frame.shape[:2]
    scale = max(0.65, height / 720.0) * ui_scale
    left = (round(steering.left_point.x * width), round(steering.left_point.y * height))
    right = (round(steering.right_point.x * width), round(steering.right_point.y * height))
    center = (
        round((steering.center.x if steering.center else 0.5) * width),
        round((steering.center.y if steering.center else 0.5) * height),
    )
    stale = bool(
        roles
        and (
            (roles.steering_left and roles.steering_left.stale)
            or (roles.steering_right and roles.steering_right.stale)
        )
    )
    color = (100, 150, 170) if stale else (50, 220, 255)
    thickness = max(2, round(line_thickness * scale))
    if show_wheel_circle:
        radius = max(20, round(math.dist(left, right) / 2))
        cv2.circle(frame, center, radius, (65, 75, 85), max(1, thickness // 2), cv2.LINE_AA)
    if stale:
        _dashed_line(frame, left, right, color, thickness)
    else:
        cv2.line(frame, left, right, (15, 15, 15), thickness + 4, cv2.LINE_AA)
        cv2.line(frame, left, right, color, thickness, cv2.LINE_AA)
    for point, grip_color in ((left, (255, 170, 40)), (right, (80, 210, 255))):
        cv2.circle(frame, point, round(10 * scale), (15, 15, 15), -1, cv2.LINE_AA)
        cv2.circle(frame, point, round(7 * scale), grip_color, -1, cv2.LINE_AA)
    cv2.circle(frame, center, round(6 * scale), color, -1, cv2.LINE_AA)
    label = (
        f"{steering.command.value.upper()}  {steering.smoothed_angle_degrees:+.1f}°  "
        f"{steering.normalized_steering_value:+.2f}"
    )
    cv2.putText(
        frame,
        label,
        (center[0] - round(100 * scale), center[1] + round(45 * scale)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65 * scale,
        color,
        max(1, round(2 * scale)),
        cv2.LINE_AA,
    )
