"""Tracking confidence scoring."""

from src.hand_tracking.confidence import score_tracking_confidence


def test_stable_visible_tracking_scores_higher() -> None:
    stable = score_tracking_confidence(1, 0.9, 0.01, 8, 0.2)
    unstable = score_tracking_confidence(0.5, 0.5, 0.18, 1, 0.2)
    stale = score_tracking_confidence(1, 0.9, 0.01, 8, 0.2, stale=True)
    assert stable.score > unstable.score
    assert stale.score < stable.score
    assert 0 <= unstable.score <= 1
