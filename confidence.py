"""Gesture confidence scoring from detection and temporal stability."""

from dataclasses import dataclass

from src.utils.geometry import clamp


@dataclass(frozen=True)
class ConfidenceComponents:
    """Explainable confidence inputs and combined score."""

    visibility: float
    tracking: float
    stability: float
    temporal: float
    score: float


def score_tracking_confidence(
    visibility: float,
    tracking_score: float,
    displacement: float,
    stable_frames: int,
    max_displacement: float,
    stale: bool = False,
) -> ConfidenceComponents:
    """Combine bounded visibility, stability, and temporal consistency."""
    visibility = clamp(visibility, 0.0, 1.0)
    tracking = clamp(tracking_score, 0.0, 1.0)
    stability = 1.0 - clamp(displacement / max(max_displacement, 1e-6), 0.0, 1.0)
    temporal = clamp(stable_frames / 8.0, 0.0, 1.0)
    score = 0.25 * visibility + 0.35 * tracking + 0.25 * stability + 0.15 * temporal
    if stale:
        score *= 0.6
    return ConfidenceComponents(visibility, tracking, stability, temporal, clamp(score, 0, 1))
