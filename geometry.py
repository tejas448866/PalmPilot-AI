"""Pure geometry helpers used by gesture processing."""

import math
from typing import Protocol


class XYPoint(Protocol):
    """A point exposing x and y coordinates."""

    @property
    def x(self) -> float:
        """Horizontal coordinate."""
        ...

    @property
    def y(self) -> float:
        """Vertical coordinate."""
        ...


def distance(a: XYPoint, b: XYPoint) -> float:
    """Return Euclidean distance between two points."""
    return math.hypot(b.x - a.x, b.y - a.y)


def midpoint(a: XYPoint, b: XYPoint) -> tuple[float, float]:
    """Return the midpoint of two points."""
    return ((a.x + b.x) / 2.0, (a.y + b.y) / 2.0)


def line_angle(a: XYPoint, b: XYPoint) -> float:
    """Return the directed line angle in degrees."""
    return math.degrees(math.atan2(b.y - a.y, b.x - a.x))


def normalize_angle(angle: float) -> float:
    """Normalize degrees to [-180, 180)."""
    return (angle + 180.0) % 360.0 - 180.0


def clamp(value: float, minimum: float, maximum: float) -> float:
    """Clamp value inclusively."""
    if minimum > maximum:
        raise ValueError("minimum cannot exceed maximum")
    return max(minimum, min(maximum, value))


def map_range(value: float, in_min: float, in_max: float, out_min: float, out_max: float) -> float:
    """Linearly map value between ranges."""
    if in_min == in_max:
        raise ValueError("input range cannot be zero")
    ratio = (value - in_min) / (in_max - in_min)
    return out_min + ratio * (out_max - out_min)
