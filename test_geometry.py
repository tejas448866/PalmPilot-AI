"""Geometry behavior."""

import pytest

from src.hand_tracking import Point2D
from src.utils.geometry import clamp, distance, line_angle, map_range, midpoint, normalize_angle


def test_distance_midpoint_and_angle() -> None:
    a, b = Point2D(0, 0), Point2D(3, 4)
    assert distance(a, b) == 5
    assert midpoint(a, b) == (1.5, 2)
    assert line_angle(Point2D(0, 0), Point2D(1, 1)) == pytest.approx(45)


def test_normalize_clamp_and_mapping() -> None:
    assert normalize_angle(190) == -170
    assert normalize_angle(-190) == 170
    assert clamp(12, 0, 10) == 10
    assert map_range(5, 0, 10, 0, 100) == 50
    with pytest.raises(ValueError):
        map_range(1, 2, 2, 0, 1)
