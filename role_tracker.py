"""Stable spatial steering roles with short lost-hand persistence."""

from dataclasses import dataclass

from src.hand_tracking.confidence import score_tracking_confidence
from src.smoothing.one_euro_filter import OneEuroPointFilter
from src.utils.constants import WRIST
from src.utils.geometry import distance

from .hand_state import DetectedHand, HandTrackingResult, Point2D
from .reference_points import calculate_reference_point


@dataclass(frozen=True)
class TrackedHand:
    """Temporal state for one steering role."""

    role: str
    detected_hand: DetectedHand
    reference_point: Point2D
    smoothed_reference_point: Point2D
    last_seen_frame: int
    last_seen_time: float
    missing_frames: int = 0
    stale: bool = False
    confidence: float = 0.0
    smoothed_wrist_point: Point2D | None = None
    stable_frames: int = 1


@dataclass(frozen=True)
class SteeringHands:
    """Current left/right steering role state."""

    steering_left: TrackedHand | None
    steering_right: TrackedHand | None

    @property
    def valid_pair(self) -> bool:
        """Whether both live-or-persisted roles are available."""
        return self.steering_left is not None and self.steering_right is not None


class HandRoleTracker:
    """Assign displayed spatial roles, smooth points, and bridge short losses."""

    def __init__(
        self,
        reference_point: str = "palm_center",
        persistence_frames: int = 6,
        persistence_ms: float = 250,
        max_reference_jump: float = 0.20,
        point_smoothing_alpha: float = 0.45,
        one_euro_enabled: bool = False,
        one_euro_min_cutoff: float = 1.0,
        one_euro_beta: float = 0.02,
        one_euro_derivative_cutoff: float = 1.0,
        nominal_frequency: float = 30.0,
        handed_mode: str = "any",
    ) -> None:
        if not 0 < point_smoothing_alpha <= 1:
            raise ValueError("point_smoothing_alpha must be in (0, 1]")
        self.strategy = reference_point
        self.persistence_frames = persistence_frames
        self.persistence_seconds = persistence_ms / 1000.0
        self.max_reference_jump = max_reference_jump
        self.alpha = point_smoothing_alpha
        self.one_euro_enabled = one_euro_enabled
        self.handed_mode = handed_mode
        self.filter_settings: tuple[float, float, float, float] = (
            one_euro_min_cutoff,
            one_euro_beta,
            one_euro_derivative_cutoff,
            nominal_frequency,
        )
        self._point_filters: dict[str, OneEuroPointFilter] = {}
        self._wrist_filters: dict[str, OneEuroPointFilter] = {}
        self.frame_index = 0
        self._roles: dict[str, TrackedHand] = {}

    def update(self, result: HandTrackingResult) -> SteeringHands:
        """Update roles from all detections, retaining short-lived stale state."""
        self.frame_index += 1
        candidates = sorted(
            (
                (calculate_reference_point(hand.landmarks, self.strategy), hand)
                for hand in result.hands
                if hand.visible
                and (
                    self.handed_mode == "any" or hand.handedness.lower() == self.handed_mode.lower()
                )
            ),
            key=lambda item: item[0].x,
        )
        assignments: dict[str, tuple[Point2D, DetectedHand]] = {}
        if len(candidates) >= 2:
            assignments = {"steering_left": candidates[0], "steering_right": candidates[-1]}
        elif len(candidates) == 1:
            point, hand = candidates[0]
            role = self._nearest_role(point)
            assignments[role] = (point, hand)
        updated: dict[str, TrackedHand] = {}
        for role in ("steering_left", "steering_right"):
            previous = self._roles.get(role)
            if role in assignments:
                point, hand = assignments[role]
                displacement = distance(previous.reference_point, point) if previous else 0.0
                if previous and displacement > self.max_reference_jump:
                    persisted = self._persist(previous, result.timestamp)
                    if persisted:
                        updated[role] = persisted
                    continue
                wrist = hand.landmarks.point(WRIST)
                if self.one_euro_enabled:
                    smoothed = self._filter_for(self._point_filters, role).update(
                        point, result.timestamp
                    )
                    smoothed_wrist = self._filter_for(self._wrist_filters, role).update(
                        wrist, result.timestamp
                    )
                else:
                    smoothed = (
                        point
                        if previous is None
                        else self._ema(previous.smoothed_reference_point, point)
                    )
                    smoothed_wrist = wrist
                stable_frames = (previous.stable_frames + 1) if previous else 1
                confidence = score_tracking_confidence(
                    float(hand.visible),
                    hand.score,
                    displacement,
                    stable_frames,
                    self.max_reference_jump,
                ).score
                updated[role] = TrackedHand(
                    role,
                    hand,
                    point,
                    smoothed,
                    self.frame_index,
                    result.timestamp,
                    confidence=confidence,
                    smoothed_wrist_point=smoothed_wrist,
                    stable_frames=stable_frames,
                )
            elif previous:
                persisted = self._persist(previous, result.timestamp)
                if persisted:
                    updated[role] = persisted
        self._roles = updated
        return SteeringHands(updated.get("steering_left"), updated.get("steering_right"))

    def _nearest_role(self, point: Point2D) -> str:
        if not self._roles:
            return "steering_left" if point.x < 0.5 else "steering_right"
        distances = {
            role: distance(state.smoothed_reference_point, point)
            for role, state in self._roles.items()
        }
        return min(distances, key=distances.__getitem__)

    def _persist(self, state: TrackedHand, timestamp: float) -> TrackedHand | None:
        missing = self.frame_index - state.last_seen_frame
        elapsed = max(0.0, timestamp - state.last_seen_time)
        if missing > self.persistence_frames or elapsed > self.persistence_seconds:
            return None
        return TrackedHand(
            state.role,
            state.detected_hand,
            state.reference_point,
            state.smoothed_reference_point,
            state.last_seen_frame,
            state.last_seen_time,
            missing,
            True,
            state.confidence,
            state.smoothed_wrist_point,
            state.stable_frames,
        )

    def _ema(self, previous: Point2D, current: Point2D) -> Point2D:
        return Point2D(
            self.alpha * current.x + (1 - self.alpha) * previous.x,
            self.alpha * current.y + (1 - self.alpha) * previous.y,
        )

    def _filter_for(self, filters: dict[str, OneEuroPointFilter], role: str) -> OneEuroPointFilter:
        if role not in filters:
            filters[role] = OneEuroPointFilter.create(*self.filter_settings)
        return filters[role]

    def tune_filter(self, min_cutoff: float, beta: float) -> None:
        """Hot-tune all palm and wrist filters without resetting state."""
        self.filter_settings = (
            min_cutoff,
            beta,
            self.filter_settings[2],
            self.filter_settings[3],
        )
        for point_filter in (*self._point_filters.values(), *self._wrist_filters.values()):
            point_filter.tune(min_cutoff, beta)
