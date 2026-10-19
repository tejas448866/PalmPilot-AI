"""Synthetic geometry tests for robust deterministic basic gestures."""

import math

import pytest

from src.gesture import DeterministicGesture, LandmarkGestureClassifier
from src.hand_tracking import DetectedHand, HandLandmarks, Point2D


def _open_points(bend: float = 0.0) -> list[Point2D]:
    points = [Point2D(0.5, 0.72) for _ in range(21)]
    points[0] = Point2D(0.5, 0.72)
    points[1:5] = [
        Point2D(0.43, 0.62),
        Point2D(0.36, 0.55),
        Point2D(0.29, 0.49 + bend),
        Point2D(0.22, 0.43 + bend),
    ]
    for chain, x in zip(
        ((5, 6, 7, 8), (9, 10, 11, 12), (13, 14, 15, 16), (17, 18, 19, 20)),
        (0.38, 0.46, 0.54, 0.62),
        strict=True,
    ):
        for index, y in zip(chain, (0.57, 0.43, 0.29, 0.15), strict=True):
            points[index] = Point2D(x + bend * (y - 0.57), y)
    return points


def _fist_points() -> list[Point2D]:
    points = _open_points()
    for chain, x in zip(
        ((5, 6, 7, 8), (9, 10, 11, 12), (13, 14, 15, 16), (17, 18, 19, 20)),
        (0.38, 0.46, 0.54, 0.62),
        strict=True,
    ):
        points[chain[0]] = Point2D(x, 0.57)
        points[chain[1]] = Point2D(x, 0.49)
        points[chain[2]] = Point2D(x + 0.055, 0.54)
        points[chain[3]] = Point2D(x + 0.02, 0.61)
    points[1:5] = [
        Point2D(0.43, 0.62),
        Point2D(0.40, 0.57),
        Point2D(0.44, 0.55),
        Point2D(0.48, 0.59),
    ]
    return points


def _transform(
    points: list[Point2D], angle_degrees: float = 0.0, scale: float = 1.0
) -> DetectedHand:
    angle = math.radians(angle_degrees)
    cosine, sine = math.cos(angle), math.sin(angle)
    transformed = tuple(
        Point2D(
            0.5 + scale * ((point.x - 0.5) * cosine - (point.y - 0.5) * sine),
            0.5 + scale * ((point.x - 0.5) * sine + (point.y - 0.5) * cosine),
        )
        for point in points
    )
    return DetectedHand("Right", 0.99, HandLandmarks(transformed, transformed))


@pytest.mark.parametrize("angle", [0.0, 28.0, -32.0])
def test_relaxed_rotated_open_palm(angle: float) -> None:
    result = LandmarkGestureClassifier().classify(_transform(_open_points(bend=0.025), angle))
    assert result.gesture is DeterministicGesture.OPEN_PALM
    assert result.extended_count >= 4


@pytest.mark.parametrize("angle", [0.0, 30.0, -25.0])
def test_rotated_closed_fist(angle: float) -> None:
    result = LandmarkGestureClassifier().classify(_transform(_fist_points(), angle))
    assert result.gesture is DeterministicGesture.CLOSED_FIST
    assert result.folded_count >= 4


def test_open_and_fist_are_scale_invariant() -> None:
    classifier = LandmarkGestureClassifier()
    assert classifier.classify(_transform(_open_points(), scale=0.55)).gesture is (
        DeterministicGesture.OPEN_PALM
    )
    assert classifier.classify(_transform(_fist_points(), scale=1.6)).gesture is (
        DeterministicGesture.CLOSED_FIST
    )


def test_mixed_pose_is_ambiguous() -> None:
    points = _open_points()
    fist = _fist_points()
    for index in (13, 14, 15, 16, 17, 18, 19, 20):
        points[index] = fist[index]
    assert LandmarkGestureClassifier().classify(_transform(points)).gesture is (
        DeterministicGesture.AMBIGUOUS
    )


def test_natural_open_hand_allows_one_bent_finger() -> None:
    points = _open_points()
    points[19] = Point2D(0.66, 0.36)
    points[20] = Point2D(0.62, 0.42)
    result = LandmarkGestureClassifier().classify(_transform(points))
    assert result.gesture is DeterministicGesture.OPEN_PALM
    assert result.extended_count >= 3


def test_open_palm_does_not_require_extended_thumb() -> None:
    points = _open_points()
    points[1:5] = [
        Point2D(0.44, 0.62),
        Point2D(0.43, 0.57),
        Point2D(0.47, 0.55),
        Point2D(0.49, 0.59),
    ]
    result = LandmarkGestureClassifier().classify(_transform(points))
    assert result.gesture is DeterministicGesture.OPEN_PALM
    assert result.finger_states[0] != "extended"


def test_relaxed_fist_allows_one_uncertain_finger() -> None:
    points = _fist_points()
    points[6] = Point2D(0.38, 0.48)
    points[7] = Point2D(0.41, 0.45)
    points[8] = Point2D(0.44, 0.43)
    result = LandmarkGestureClassifier().classify(_transform(points))
    assert result.gesture is DeterministicGesture.CLOSED_FIST
    assert result.folded_count >= 3
