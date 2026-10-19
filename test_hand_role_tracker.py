"""Spatial role assignment, point strategy, persistence, and jump tests."""

from src.hand_tracking import HandRoleTracker, HandTrackingResult, Point2D
from src.hand_tracking.reference_points import calculate_reference_point
from tests.fixtures.sample_landmarks import make_hand, make_two_hands


def test_palm_center_calculation() -> None:
    hand = make_hand("Unknown", 0.4, 0.6)
    assert calculate_reference_point(hand.landmarks) == Point2D(0.4, 0.6)


def test_both_hands_retained_and_roles_use_display_x() -> None:
    tracker = HandRoleTracker(point_smoothing_alpha=1)
    roles = tracker.update(make_two_hands())
    assert roles.valid_pair
    assert roles.steering_left
    assert roles.steering_right
    assert roles.steering_left.smoothed_reference_point.x == 0.3
    assert roles.steering_right.smoothed_reference_point.x == 0.7
    # Handedness metadata is not used as steering identity.
    assert roles.steering_left.detected_hand.handedness == "Left"


def test_minor_jitter_does_not_swap_roles_and_ema_smooths() -> None:
    tracker = HandRoleTracker(point_smoothing_alpha=0.5)
    tracker.update(make_two_hands())
    jittered = HandTrackingResult(
        (make_hand("Right", 0.31, 0.5), make_hand("Left", 0.69, 0.5)), 0.01
    )
    roles = tracker.update(jittered)
    assert roles.steering_left
    assert roles.steering_right
    assert roles.steering_left.smoothed_reference_point.x == 0.305
    assert roles.steering_right.smoothed_reference_point.x == 0.695


def test_missing_hand_persists_then_expires() -> None:
    tracker = HandRoleTracker(persistence_frames=2, persistence_ms=1000, point_smoothing_alpha=1)
    tracker.update(HandTrackingResult(make_two_hands().hands, 1.0))
    one = HandTrackingResult((make_hand("Left", 0.3, 0.5),), 1.1)
    assert tracker.update(one).valid_pair
    assert tracker.update(one).valid_pair
    assert not tracker.update(one).valid_pair


def test_point_jump_is_rejected_as_stale() -> None:
    tracker = HandRoleTracker(max_reference_jump=0.1, point_smoothing_alpha=1)
    tracker.update(HandTrackingResult(make_two_hands().hands, 1.0))
    jumped = HandTrackingResult((make_hand("Left", 0.05, 0.1), make_hand("Right", 0.95, 0.9)), 1.1)
    roles = tracker.update(jumped)
    assert roles.steering_left and roles.steering_left.stale
    assert roles.steering_right and roles.steering_right.stale
