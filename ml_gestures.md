# ML gesture recognition

The ML engine recognizes discrete auxiliary and pedal gestures. Continuous steering still
uses the calibrated two-hand wheel geometry because regression-like wheel motion is better
represented by its stable continuous signal than by gesture classes.

## Components

- `src/ml/features.py` owns the versioned 70-value feature schema.
- `src/ml/dataset.py` owns validated JSONL storage, duplicate detection, and export.
- `src/ml/training.py` owns repeatable model selection and evaluation artifacts.
- `src/ml/inference.py` owns confidence rejection and low-cost temporal voting.
- `src/ml/action_mapping.py` maps model labels to existing abstract commands.

Model files are deliberately separate from source control configuration. Metadata records
the feature schema and input width so an incompatible model fails closed.

## Collection

Capture at least 100 varied samples per class, use balanced class counts, and include an
explicit neutral/no-action class if neutral hand poses resemble active gestures. Duplicate
frames are rejected after feature quantization. Collect a new validation session after
training; consecutive webcam frames are correlated and can otherwise make metrics appear
better than real gameplay.

## Evaluation

Review weighted precision, recall, F1, the per-class classification report, and confusion
matrix—not accuracy alone. Increase the confidence threshold when false activations are
costly. Increase the smoothing window only when predictions flicker; larger windows delay
action changes.

## Runtime safety

ML is opt-in. Unknown and below-threshold predictions produce no mapped ML action.
Unavailable dependencies, missing artifacts, and mismatched feature schemas use the
existing rule-based detector. Keyboard cleanup, dry-run, tracking-loss release, replay,
and calibration paths are unchanged.

## Current boundaries

Version 5 intentionally does not add neural-network training, sequence models, cloud
training, automatic dataset uploads, or online model updates. Those would add deployment,
privacy, and reproducibility costs without evidence that they improve this controller.
