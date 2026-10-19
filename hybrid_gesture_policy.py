"""Immediate deterministic gesture control with frame-based hysteresis."""

from dataclasses import dataclass

from .landmark_gesture_classifier import DeterministicGesture


@dataclass(frozen=True)
class HybridGestureConfig:
    """Frame counts for instant clear actions and brief noise tolerance."""

    clear_gesture_frames: int = 1
    ml_gesture_frames: int = 3
    ambiguous_release_frames: int = 3
    hand_lost_release_frames: int = 3
    action_switch_frames: int = 1


@dataclass(frozen=True)
class HybridGestureDecision:
    """Final stable gesture and its transition diagnostics."""

    final_gesture: str
    stability_frames: int
    reason: str


class HybridGesturePolicy:
    """Give clear landmarks immediate precedence without time-based holds."""

    def __init__(self, config: HybridGestureConfig | None = None) -> None:
        self.config = config or HybridGestureConfig()
        self.active_gesture = "idle"
        self.candidate = "idle"
        self.candidate_frames = 0
        self.ambiguous_frames = 0
        self.missing_frames = 0

    def update(
        self,
        deterministic: DeterministicGesture,
        ml_gesture: str | None,
        hand_detected: bool,
        supporting_gesture: str | None = None,
    ) -> HybridGestureDecision:
        """Update state with first-frame clear activation and switching."""
        if not hand_detected:
            self.missing_frames += 1
            self.ambiguous_frames = 0
            self._reset_candidate()
            if (
                self.active_gesture != "idle"
                and self.missing_frames < self.config.hand_lost_release_frames
            ):
                return HybridGestureDecision(
                    self.active_gesture,
                    self.missing_frames,
                    "preserving active action during brief hand loss",
                )
            self.active_gesture = "idle"
            return HybridGestureDecision(
                "idle", self.missing_frames, "missing-hand frame limit reached"
            )

        self.missing_frames = 0
        if deterministic is not DeterministicGesture.AMBIGUOUS:
            self.ambiguous_frames = 0
            target = deterministic.value
            required = (
                self.config.clear_gesture_frames
                if self.active_gesture == "idle"
                else self.config.action_switch_frames
            )
            return self._advance(target, required, "clear landmark gesture")

        if self.active_gesture != "idle":
            if supporting_gesture == self.active_gesture or ml_gesture == self.active_gesture:
                self.ambiguous_frames = 0
                self._reset_candidate()
                return HybridGestureDecision(
                    self.active_gesture,
                    0,
                    "weak evidence supports active action",
                )
            self.ambiguous_frames += 1
            self._reset_candidate()
            if self.ambiguous_frames < self.config.ambiguous_release_frames:
                return HybridGestureDecision(
                    self.active_gesture,
                    self.ambiguous_frames,
                    "preserving active action during one uncertain frame",
                )
            self.active_gesture = "idle"
            return HybridGestureDecision(
                "idle",
                self.ambiguous_frames,
                "repeated ambiguous frames; conflicting ML ignored",
            )

        self.ambiguous_frames += 1
        if ml_gesture and ml_gesture != "unknown":
            return self._advance(
                ml_gesture,
                self.config.ml_gesture_frames,
                "ambiguous landmarks; using stabilized ML",
            )
        self._reset_candidate()
        return HybridGestureDecision("idle", self.ambiguous_frames, "ambiguous pose; no action")

    def reset(self) -> None:
        """Return immediately to safe idle."""
        self.active_gesture = "idle"
        self.ambiguous_frames = 0
        self.missing_frames = 0
        self._reset_candidate()

    def _advance(self, target: str, required_frames: int, reason: str) -> HybridGestureDecision:
        if target == self.active_gesture:
            self._reset_candidate()
            return HybridGestureDecision(target, required_frames, reason)
        if target == self.candidate:
            self.candidate_frames += 1
        else:
            self.candidate = target
            self.candidate_frames = 1
        if self.candidate_frames >= required_frames:
            self.active_gesture = target
            frames = self.candidate_frames
            self._reset_candidate()
            return HybridGestureDecision(target, frames, f"activated: {reason}")
        return HybridGestureDecision(
            self.active_gesture,
            self.candidate_frames,
            f"waiting for {target}: {self.candidate_frames}/{required_frames}",
        )

    def _reset_candidate(self) -> None:
        self.candidate = "idle"
        self.candidate_frames = 0
