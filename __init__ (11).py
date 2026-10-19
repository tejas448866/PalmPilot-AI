"""Machine-learning gesture recognition engine."""

from .action_mapping import GestureActionMapping
from .capture_policy import CaptureDecision, CaptureState, DatasetCapturePolicy
from .dataset import DatasetValidation, GestureDataset, GestureSample
from .features import FeatureVector, HandFeatureExtractor
from .inference import (
    GestureInferenceEngine,
    GesturePrediction,
    RecognitionDiagnostics,
    load_engine_or_none,
    resolve_model_path,
)
from .runtime_control import (
    MappedGestureActions,
    resolve_mapped_actions,
    select_pedal_command,
)
from .training import GestureModelTrainer, TrainingConfig, TrainingResult

__all__ = [
    "DatasetValidation",
    "CaptureDecision",
    "CaptureState",
    "DatasetCapturePolicy",
    "FeatureVector",
    "GestureActionMapping",
    "GestureDataset",
    "GestureInferenceEngine",
    "GestureModelTrainer",
    "GesturePrediction",
    "RecognitionDiagnostics",
    "GestureSample",
    "HandFeatureExtractor",
    "MappedGestureActions",
    "TrainingConfig",
    "TrainingResult",
    "resolve_model_path",
    "load_engine_or_none",
    "resolve_mapped_actions",
    "select_pedal_command",
]
