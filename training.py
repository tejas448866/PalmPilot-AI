"""Reproducible scikit-learn model selection and evaluation."""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .dataset import GestureDataset


@dataclass(frozen=True)
class TrainingConfig:
    """Model-selection parameters."""

    algorithms: tuple[str, ...] = ("random_forest", "svm", "knn", "logistic_regression")
    validation_size: float = 0.2
    cross_validation_folds: int = 5
    random_state: int = 42
    scoring: str = "f1_weighted"


@dataclass(frozen=True)
class TrainingResult:
    """Paths and headline score from training."""

    model_path: Path
    metadata_path: Path
    evaluation_path: Path
    best_algorithm: str
    validation_accuracy: float


class GestureModelTrainer:
    """Compare supported estimators and persist the best validated pipeline."""

    def __init__(self, config: TrainingConfig | None = None) -> None:
        self.config = config or TrainingConfig()

    def train(self, dataset: GestureDataset, output_directory: Path) -> TrainingResult:
        """Train with stratified holdout, CV, and bounded hyperparameter search."""
        samples = dataset.load()
        labels = sorted({sample.label for sample in samples})
        if len(labels) < 2:
            raise ValueError("Training requires at least two gesture labels")
        counts = {label: sum(sample.label == label for sample in samples) for label in labels}
        minimum = min(counts.values())
        if minimum < 3:
            raise ValueError("Each gesture needs at least three samples")
        try:
            import joblib
            import numpy as np
            from sklearn.calibration import CalibratedClassifierCV
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.linear_model import LogisticRegression
            from sklearn.metrics import (
                accuracy_score,
                classification_report,
                confusion_matrix,
                precision_recall_fscore_support,
            )
            from sklearn.model_selection import GridSearchCV, train_test_split
            from sklearn.neighbors import KNeighborsClassifier
            from sklearn.pipeline import Pipeline
            from sklearn.preprocessing import StandardScaler
            from sklearn.svm import SVC
        except ImportError as exc:
            raise RuntimeError("Model training requires scikit-learn, joblib, and NumPy") from exc
        x = np.asarray([sample.features for sample in samples], dtype=np.float32)
        y = np.asarray([sample.label for sample in samples])
        x_train, x_valid, y_train, y_valid = train_test_split(
            x,
            y,
            test_size=self.config.validation_size,
            random_state=self.config.random_state,
            stratify=y,
        )
        training_counts = {label: int(np.count_nonzero(y_train == label)) for label in labels}
        effective_folds = min(self.config.cross_validation_folds, min(training_counts.values()))
        if effective_folds < 2:
            raise ValueError("Training split leaves too few samples for cross-validation")
        candidates: dict[str, tuple[Any, dict[str, list[Any]]]] = {
            "random_forest": (
                RandomForestClassifier(
                    random_state=self.config.random_state, class_weight="balanced"
                ),
                {"model__n_estimators": [100, 200], "model__max_depth": [None, 12]},
            ),
            "svm": (
                CalibratedClassifierCV(
                    SVC(
                        class_weight="balanced",
                        random_state=self.config.random_state,
                    ),
                    cv=3,
                    ensemble=False,
                ),
                {
                    "model__estimator__C": [1.0, 10.0],
                    "model__estimator__kernel": ["rbf", "linear"],
                },
            ),
            "knn": (
                KNeighborsClassifier(),
                {"model__n_neighbors": [3, 5, 7], "model__weights": ["uniform", "distance"]},
            ),
            "logistic_regression": (
                LogisticRegression(
                    max_iter=2000,
                    class_weight="balanced",
                    random_state=self.config.random_state,
                ),
                {"model__C": [0.1, 1.0, 10.0]},
            ),
        }
        searches: dict[str, Any] = {}
        for name in self.config.algorithms:
            if name not in candidates:
                raise ValueError(f"Unsupported algorithm: {name}")
            estimator, parameters = candidates[name]
            pipeline = Pipeline([("scale", StandardScaler()), ("model", estimator)])
            search = GridSearchCV(
                pipeline,
                parameters,
                cv=effective_folds,
                scoring=self.config.scoring,
                n_jobs=-1,
            )
            search.fit(x_train, y_train)
            searches[name] = search
        best_name, best_search = max(searches.items(), key=lambda item: float(item[1].best_score_))
        predictions = best_search.best_estimator_.predict(x_valid)
        accuracy = float(accuracy_score(y_valid, predictions))
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_valid, predictions, average="weighted", zero_division=0
        )
        evaluation = {
            "accuracy": accuracy,
            "precision_weighted": float(precision),
            "recall_weighted": float(recall),
            "f1_weighted": float(f1),
            "confusion_matrix": confusion_matrix(y_valid, predictions, labels=labels).tolist(),
            "labels": labels,
            "classification_report": classification_report(
                y_valid, predictions, labels=labels, output_dict=True, zero_division=0
            ),
            "cross_validation": {
                name: {
                    "best_score": float(search.best_score_),
                    "best_parameters": search.best_params_,
                }
                for name, search in searches.items()
            },
        }
        output_directory.mkdir(parents=True, exist_ok=True)
        model_path = output_directory / "gesture_model.joblib"
        metadata_path = output_directory / "gesture_model.metadata.json"
        evaluation_path = output_directory / "gesture_model.evaluation.json"
        joblib.dump(best_search.best_estimator_, model_path)
        metadata_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "feature_schema": "hand_features_v1",
                    "feature_count": dataset.feature_count,
                    "classes": labels,
                    "algorithm": best_name,
                    "training_samples": len(samples),
                    "random_state": self.config.random_state,
                    "cross_validation_folds": effective_folds,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        evaluation_path.write_text(json.dumps(evaluation, indent=2), encoding="utf-8")
        return TrainingResult(model_path, metadata_path, evaluation_path, best_name, accuracy)
