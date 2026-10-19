"""Low-latency model inference with unknown handling and temporal smoothing."""

import json
import logging
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.hand_tracking import DetectedHand
from src.utils.resources import application_root

from .features import HandFeatureExtractor

LOGGER = logging.getLogger(__name__)


def resolve_model_path(path: Path, project_root: Path | None = None) -> Path:
    """Resolve configured artifacts from the project root, independent of cwd."""
    root = project_root or application_root()
    return path.resolve() if path.is_absolute() else (root / path).resolve()


@dataclass(frozen=True)
class GesturePrediction:
    """One stable gesture prediction."""

    label: str
    confidence: float
    raw_label: str
    known: bool
    rejection_reason: str | None = None


@dataclass(frozen=True)
class RecognitionDiagnostics:
    """Current recognizer state consumed by logging and the HUD."""

    mode: str
    model_loaded: bool
    raw_label: str = "none"
    stable_label: str = "none"
    confidence: float = 0.0
    mapped_action: str = "idle"
    rejection_reason: str | None = None
    hand_detected: bool = False
    finger_states: tuple[str, ...] = ()
    openness_score: float = 0.0
    deterministic_gesture: str = "none"
    ml_gesture: str = "none"
    final_gesture: str = "idle"
    stability_frames: int = 0


class GestureInferenceEngine:
    """Load a trained pipeline once and infer one hand per frame."""

    def __init__(
        self,
        model_path: Path,
        metadata_path: Path,
        confidence_threshold: float = 0.65,
        smoothing_window: int = 5,
        unknown_label: str = "unknown",
        extractor: HandFeatureExtractor | None = None,
    ) -> None:
        if not 0 <= confidence_threshold <= 1 or smoothing_window < 1:
            raise ValueError("Invalid inference configuration")
        try:
            import joblib
        except ImportError as exc:
            raise RuntimeError("Gesture inference requires joblib") from exc
        self.model_path = resolve_model_path(model_path)
        self.metadata_path = resolve_model_path(metadata_path)
        metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        self.extractor = extractor or HandFeatureExtractor()
        if metadata.get("feature_schema") != self.extractor.schema:
            raise ValueError("Model feature schema is incompatible")
        if int(metadata.get("feature_count", -1)) != self.extractor.feature_count:
            raise ValueError("Model feature count is incompatible")
        self.model: Any = joblib.load(self.model_path)
        if not callable(getattr(self.model, "predict_proba", None)):
            raise ValueError("Model does not provide probability predictions")
        model_classes = tuple(str(value) for value in getattr(self.model, "classes_", ()))
        metadata_classes = tuple(str(value) for value in metadata.get("classes", ()))
        if not model_classes or model_classes != metadata_classes:
            raise ValueError("Model classes do not match metadata")
        self.classes = model_classes
        self.algorithm = str(metadata.get("algorithm", "unknown"))
        self.threshold = confidence_threshold
        self.unknown_label = unknown_label
        self.history: deque[str] = deque(maxlen=smoothing_window)
        self.stable_label = unknown_label

    def predict(self, hand: DetectedHand) -> GesturePrediction:
        """Predict and stabilize a gesture without retaining image frames."""
        features = self.extract_features(hand)
        if len(features) != self.extractor.feature_count:
            raise ValueError("Runtime feature count does not match model input")
        probabilities = self.model.predict_proba([features])[0]
        classes = self.model.classes_
        best_index = max(range(len(probabilities)), key=probabilities.__getitem__)
        raw_label, confidence = str(classes[best_index]), float(probabilities[best_index])
        accepted = raw_label if confidence >= self.threshold else self.unknown_label
        self.history.append(accepted)
        if len(self.history) == self.history.maxlen and len(set(self.history)) == 1:
            self.stable_label = accepted
        stable = self.stable_label
        reason = (
            f"confidence {confidence:.3f} below threshold {self.threshold:.3f}"
            if accepted == self.unknown_label
            else None
        )
        return GesturePrediction(
            stable,
            confidence,
            raw_label,
            stable != self.unknown_label,
            reason,
        )

    def extract_features(self, hand: DetectedHand) -> tuple[float, ...]:
        """Use the shared training/recording feature transformation."""
        return self.extractor.extract(hand).values

    def reset(self) -> None:
        """Clear prediction history after tracking loss."""
        self.history.clear()
        self.stable_label = self.unknown_label


def load_engine_or_none(**kwargs: Any) -> GestureInferenceEngine | None:
    """Gracefully return no engine for missing or incompatible artifacts."""
    try:
        return GestureInferenceEngine(**kwargs)
    except (FileNotFoundError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        LOGGER.error("ML model loading failed: %s", exc)
        return None
