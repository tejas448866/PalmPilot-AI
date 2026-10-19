"""Continuous virtual steering geometry with validation and hysteresis."""

from dataclasses import dataclass

from src.hand_tracking import Point2D, SteeringHands
from src.smoothing import OneEuroAngleFilter
from src.smoothing.angle_smoothing import AngleSmoother, angular_delta
from src.utils.geometry import clamp, distance, line_angle, midpoint, normalize_angle

from .gesture_state import Command
from .response_curves import apply_response_curve
from .steering_profiles import SteeringProfile


def normalize_steering_value(angle: float, left_range: float, right_range: float) -> float:
    """Normalize asymmetric calibrated steering ranges to [-1, 1]."""
    if left_range <= 0 or right_range <= 0:
        raise ValueError("steering ranges must be positive")
    divisor = left_range if angle < 0 else right_range
    return clamp(angle / divisor, -1.0, 1.0)


@dataclass(frozen=True)
class SteeringResult:
    """Continuous wheel metrics and discrete command."""

    command: Command
    raw_angle_degrees: float | None
    calibrated_angle_degrees: float | None
    smoothed_angle_degrees: float
    normalized_steering_value: float
    wheel_span: float
    valid: bool
    confidence: float
    left_point: Point2D | None = None
    right_point: Point2D | None = None
    center: Point2D | None = None
    reason: str = ""
    profile_name: str = "Normal"

    @property
    def angle(self) -> float | None:
        """Backward-compatible displayed steering angle."""
        return self.smoothed_angle_degrees if self.valid else None


class SteeringDetector:
    """Calculate a stable continuous wheel model and hysteretic direction."""

    def __init__(
        self,
        neutral_angle: float = 0.0,
        invert: bool = False,
        minimum_hand_span: float = 0.12,
        enter_left_threshold: float = -12.0,
        exit_left_threshold: float = -7.0,
        enter_right_threshold: float = 12.0,
        exit_right_threshold: float = 7.0,
        maximum_angle: float = 60.0,
        normalized_left_range: float | None = None,
        normalized_right_range: float | None = None,
        angle_smoothing_alpha: float = 0.35,
        median_window: int = 3,
        max_angle_jump: float = 25.0,
        one_euro_enabled: bool = True,
        one_euro_min_cutoff: float = 1.0,
        one_euro_beta: float = 0.025,
        one_euro_derivative_cutoff: float = 1.0,
        nominal_frequency: float = 30.0,
        response_curve: str = "linear",
        curve_strength: float = 2.0,
        minimum_confidence: float = 0.50,
        profile_name: str = "Normal",
        steering_mode: str = "two_hand",
        handed_mode: str = "any",
        **legacy: object,
    ) -> None:
        if not (enter_left_threshold < exit_left_threshold <= 0):
            raise ValueError("left hysteresis thresholds are invalid")
        if not (0 <= exit_right_threshold < enter_right_threshold):
            raise ValueError("right hysteresis thresholds are invalid")
        self.neutral_angle = neutral_angle
        self.invert = invert
        self.minimum_hand_span = minimum_hand_span
        self.enter_left = enter_left_threshold
        self.exit_left = exit_left_threshold
        self.enter_right = enter_right_threshold
        self.exit_right = exit_right_threshold
        self.maximum_angle = maximum_angle
        self.normalized_left_range = normalized_left_range or maximum_angle
        self.normalized_right_range = normalized_right_range or maximum_angle
        self.max_angle_jump = max_angle_jump
        self.one_euro_enabled = one_euro_enabled
        self.one_euro = OneEuroAngleFilter(
            one_euro_min_cutoff,
            one_euro_beta,
            one_euro_derivative_cutoff,
            nominal_frequency,
        )
        self.smoother = AngleSmoother(angle_smoothing_alpha, median_window)
        self.response_curve = response_curve
        self.curve_strength = curve_strength
        self.minimum_confidence = minimum_confidence
        self.profile_name = profile_name
        self.steering_mode = steering_mode
        self.handed_mode = handed_mode
        self.command = Command.STRAIGHT
        self.last_raw_angle: float | None = None

    def detect(self, hands: SteeringHands) -> SteeringResult:
        """Calculate steering from temporally assigned roles."""
        if not hands.valid_pair:
            if self.steering_mode == "single_hand":
                tracked = hands.steering_left or hands.steering_right
                if tracked and not tracked.stale:
                    if tracked.confidence < self.minimum_confidence:
                        return self._invalid("single-hand confidence below threshold")
                    angle = (tracked.smoothed_reference_point.x - 0.5) * 2.0
                    angle *= self.maximum_angle
                    if self.invert:
                        angle = -angle
                    smoothed = self.one_euro.update(angle, tracked.last_seen_time)
                    self.command = self.command_for_angle(smoothed)
                    normalized = apply_response_curve(
                        normalize_steering_value(
                            smoothed,
                            self.normalized_left_range,
                            self.normalized_right_range,
                        ),
                        self.response_curve,
                        self.curve_strength,
                    )
                    return SteeringResult(
                        self.command,
                        angle,
                        angle,
                        smoothed,
                        normalized,
                        0.0,
                        True,
                        tracked.confidence,
                        profile_name=self.profile_name,
                        reason="single hand",
                    )
            return self._invalid("two steering hands unavailable")
        assert hands.steering_left and hands.steering_right
        stale_count = int(hands.steering_left.stale) + int(hands.steering_right.stale)
        confidence = min(hands.steering_left.confidence, hands.steering_right.confidence)
        confidence *= 1.0 - 0.25 * stale_count
        if confidence < self.minimum_confidence:
            return self._invalid("confidence below threshold")
        left = hands.steering_left.smoothed_reference_point
        right = hands.steering_right.smoothed_reference_point
        if not self._valid_point(left) or not self._valid_point(right):
            return self._invalid("invalid normalized coordinates")
        span = distance(left, right)
        if span < self.minimum_hand_span:
            return self._invalid("hand span below minimum", left, right, span)
        raw = normalize_angle(line_angle(left, right))
        if (
            self.last_raw_angle is not None
            and abs(angular_delta(raw, self.last_raw_angle)) > self.max_angle_jump
        ):
            return self._invalid("angle jump rejected", left, right, span)
        self.last_raw_angle = raw
        calibrated = normalize_angle(raw - self.neutral_angle)
        if self.invert:
            calibrated = -calibrated
        timestamp = max(hands.steering_left.last_seen_time, hands.steering_right.last_seen_time)
        smoothed = (
            self.one_euro.update(calibrated, timestamp)
            if self.one_euro_enabled
            else self.smoother.update(calibrated)
        )
        self.command = self.command_for_angle(smoothed)
        normalized = apply_response_curve(
            normalize_steering_value(
                smoothed, self.normalized_left_range, self.normalized_right_range
            ),
            self.response_curve,
            self.curve_strength,
        )
        center_xy = midpoint(left, right)
        return SteeringResult(
            self.command,
            raw,
            calibrated,
            smoothed,
            normalized,
            span,
            True,
            confidence,
            left,
            right,
            Point2D(*center_xy),
            "stale persistence" if stale_count else "live",
            self.profile_name,
        )

    def command_for_angle(self, angle: float) -> Command:
        """Update the four-threshold direction state machine."""
        if self.command is Command.LEFT:
            if angle >= self.exit_left:
                self.command = Command.RIGHT if angle >= self.enter_right else Command.STRAIGHT
        elif self.command is Command.RIGHT:
            if angle <= self.exit_right:
                self.command = Command.LEFT if angle <= self.enter_left else Command.STRAIGHT
        elif angle <= self.enter_left:
            self.command = Command.LEFT
        elif angle >= self.enter_right:
            self.command = Command.RIGHT
        else:
            self.command = Command.STRAIGHT
        return self.command

    def _invalid(
        self,
        reason: str,
        left: Point2D | None = None,
        right: Point2D | None = None,
        span: float = 0.0,
    ) -> SteeringResult:
        self.command = Command.STRAIGHT
        self.smoother.reset()
        self.one_euro.reset()
        self.last_raw_angle = None
        return SteeringResult(
            Command.STRAIGHT,
            None,
            None,
            0.0,
            0.0,
            span,
            False,
            0.0,
            left,
            right,
            reason=reason,
            profile_name=self.profile_name,
        )

    @staticmethod
    def _valid_point(point: Point2D) -> bool:
        return 0.0 <= point.x <= 1.0 and 0.0 <= point.y <= 1.0

    def apply_profile(self, profile: SteeringProfile) -> None:
        """Hot-apply sensitivity, response, and filter strength."""
        self.profile_name = profile.name.title()
        self.maximum_angle = profile.maximum_angle
        self.normalized_left_range = profile.maximum_angle
        self.normalized_right_range = profile.maximum_angle
        self.exit_left = -profile.dead_zone
        self.exit_right = profile.dead_zone
        self.enter_left = -(profile.dead_zone + 3.0)
        self.enter_right = profile.dead_zone + 3.0
        self.response_curve = profile.response_curve
        self.curve_strength = profile.curve_strength
        self.one_euro.tune(profile.min_cutoff, profile.beta)
