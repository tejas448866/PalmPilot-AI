"""Train and evaluate gesture classifiers from a validated JSONL dataset."""

import argparse
from pathlib import Path

try:
    from scripts import _bootstrap  # noqa: F401
except ModuleNotFoundError:
    import _bootstrap  # type: ignore[no-redef]  # noqa: F401

from src.ml import GestureDataset, GestureModelTrainer, HandFeatureExtractor, TrainingConfig


def main() -> int:
    """Train supported models and print persisted artifact locations."""
    parser = argparse.ArgumentParser(description="Train the ML gesture recognizer")
    parser.add_argument("--dataset", type=Path, default=Path("data/processed/gestures.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("models/trained"))
    parser.add_argument("--cv-folds", type=int, default=5)
    parser.add_argument(
        "--algorithms",
        nargs="+",
        default=["random_forest", "svm", "knn", "logistic_regression"],
    )
    args = parser.parse_args()
    dataset = GestureDataset(args.dataset, HandFeatureExtractor().feature_count)
    try:
        result = GestureModelTrainer(
            TrainingConfig(tuple(args.algorithms), cross_validation_folds=args.cv_folds)
        ).train(dataset, args.output)
    except (RuntimeError, ValueError, OSError) as exc:
        print(f"Training failed: {exc}")
        return 1
    print(f"Best algorithm: {result.best_algorithm}")
    print(f"Validation accuracy: {result.validation_accuracy:.3f}")
    print(f"Model: {result.model_path}")
    print(f"Metadata: {result.metadata_path}")
    print(f"Evaluation: {result.evaluation_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
