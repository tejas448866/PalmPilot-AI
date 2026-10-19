"""Tests for immediate actions and frame-based gesture hysteresis."""

from src.gesture import (
    DeterministicGesture,
    HybridGestureConfig,
    HybridGesturePolicy,
)


def test_clear_gesture_activates_on_first_frame() -> None:
    decision = HybridGesturePolicy().update(DeterministicGesture.OPEN_PALM, None, True)
    assert decision.final_gesture == "open_palm"


def test_clear_opposite_gesture_switches_on_first_frame() -> None:
    policy = HybridGesturePolicy()
    policy.update(DeterministicGesture.OPEN_PALM, None, True)
    decision = policy.update(DeterministicGesture.CLOSED_FIST, None, True)
    assert decision.final_gesture == "closed_fist"


def test_one_ambiguous_frame_preserves_active_action() -> None:
    policy = HybridGesturePolicy()
    policy.update(DeterministicGesture.OPEN_PALM, None, True)
    decision = policy.update(DeterministicGesture.AMBIGUOUS, None, True)
    assert decision.final_gesture == "open_palm"
    assert "one uncertain frame" in decision.reason


def test_repeated_ambiguity_releases_to_idle() -> None:
    policy = HybridGesturePolicy(HybridGestureConfig(ambiguous_release_frames=3))
    policy.update(DeterministicGesture.OPEN_PALM, None, True)
    policy.update(DeterministicGesture.AMBIGUOUS, None, True)
    policy.update(DeterministicGesture.AMBIGUOUS, None, True)
    decision = policy.update(DeterministicGesture.AMBIGUOUS, None, True)
    assert decision.final_gesture == "idle"


def test_missing_hand_frames_release_action() -> None:
    policy = HybridGesturePolicy(HybridGestureConfig(hand_lost_release_frames=3))
    policy.update(DeterministicGesture.CLOSED_FIST, None, True)
    policy.update(DeterministicGesture.AMBIGUOUS, None, False)
    assert policy.active_gesture == "closed_fist"
    policy.update(DeterministicGesture.AMBIGUOUS, None, False)
    decision = policy.update(DeterministicGesture.AMBIGUOUS, None, False)
    assert decision.final_gesture == "idle"


def test_deterministic_result_precedes_conflicting_ml() -> None:
    decision = HybridGesturePolicy().update(DeterministicGesture.OPEN_PALM, "closed_fist", True)
    assert decision.final_gesture == "open_palm"


def test_conflicting_ml_cannot_switch_active_deterministic_action() -> None:
    policy = HybridGesturePolicy(HybridGestureConfig(ambiguous_release_frames=3))
    policy.update(DeterministicGesture.OPEN_PALM, None, True)
    first = policy.update(DeterministicGesture.AMBIGUOUS, "closed_fist", True)
    second = policy.update(DeterministicGesture.AMBIGUOUS, "closed_fist", True)
    assert first.final_gesture == second.final_gesture == "open_palm"


def test_weak_same_gesture_evidence_maintains_active_action() -> None:
    policy = HybridGesturePolicy()
    policy.update(DeterministicGesture.OPEN_PALM, None, True)
    for _ in range(10):
        decision = policy.update(
            DeterministicGesture.AMBIGUOUS,
            "closed_fist",
            True,
            supporting_gesture="open_palm",
        )
        assert decision.final_gesture == "open_palm"
