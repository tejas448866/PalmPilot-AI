"""Validated JSONL gesture dataset storage."""

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class GestureSample:
    """One labeled model feature row."""

    label: str
    features: tuple[float, ...]
    handedness: str
    timestamp: float
    source: str = "webcam"


@dataclass(frozen=True)
class DatasetValidation:
    """Dataset completeness and duplicate report."""

    total_samples: int
    labels: dict[str, int]
    duplicate_count: int
    invalid_count: int
    missing_by_label: dict[str, int]

    @property
    def valid(self) -> bool:
        """Whether no invalid or required samples are missing."""
        return self.invalid_count == 0 and not any(self.missing_by_label.values())


class GestureDataset:
    """Append, deduplicate, validate, and export gesture samples."""

    schema_version = 1

    def __init__(self, path: Path, feature_count: int) -> None:
        self.path = path
        self.feature_count = feature_count

    @staticmethod
    def fingerprint(sample: GestureSample) -> str:
        """Hash rounded geometry to identify near-identical captures."""
        payload = f"{sample.label}:" + ",".join(f"{value:.5f}" for value in sample.features)
        return hashlib.sha256(payload.encode()).hexdigest()

    def append(self, sample: GestureSample, reject_duplicate: bool = True) -> bool:
        """Append one valid sample; return false for a rejected duplicate."""
        self._validate_sample(sample)
        if reject_duplicate:
            fingerprints = {self.fingerprint(existing) for existing in self.load()}
            if self.fingerprint(sample) in fingerprints:
                return False
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as stream:
            data = asdict(sample)
            data["features"] = list(sample.features)
            stream.write(json.dumps(data) + "\n")
        return True

    def load(self) -> list[GestureSample]:
        """Load all well-formed JSONL rows."""
        if not self.path.exists():
            return []
        samples: list[GestureSample] = []
        for line_number, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
            try:
                data = json.loads(line)
                sample = GestureSample(
                    str(data["label"]),
                    tuple(float(value) for value in data["features"]),
                    str(data["handedness"]),
                    float(data["timestamp"]),
                    str(data.get("source", "webcam")),
                )
                self._validate_sample(sample)
                samples.append(sample)
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                raise ValueError(f"Invalid dataset row {line_number}: {exc}") from exc
        return samples

    def validate(self, required: dict[str, int] | None = None) -> DatasetValidation:
        """Report duplicates, malformed rows, and missing class samples."""
        samples = self.load()
        labels: dict[str, int] = {}
        fingerprints: set[str] = set()
        duplicates = 0
        for sample in samples:
            labels[sample.label] = labels.get(sample.label, 0) + 1
            fingerprint = self.fingerprint(sample)
            duplicates += int(fingerprint in fingerprints)
            fingerprints.add(fingerprint)
        missing = {
            label: max(0, count - labels.get(label, 0)) for label, count in (required or {}).items()
        }
        return DatasetValidation(len(samples), labels, duplicates, 0, missing)

    def export(self, destination: Path) -> tuple[Path, Path]:
        """Copy JSONL data and write a reproducibility manifest."""
        samples = self.load()
        destination.mkdir(parents=True, exist_ok=True)
        data_path = destination / "gesture_samples.jsonl"
        data_path.write_text(self.path.read_text(encoding="utf-8"), encoding="utf-8")
        manifest = destination / "manifest.json"
        report = self.validate()
        manifest.write_text(
            json.dumps(
                {
                    "schema_version": self.schema_version,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "feature_count": self.feature_count,
                    "sample_count": len(samples),
                    "labels": report.labels,
                    "sha256": hashlib.sha256(data_path.read_bytes()).hexdigest(),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return data_path, manifest

    def _validate_sample(self, sample: GestureSample) -> None:
        if not sample.label.strip():
            raise ValueError("Gesture label cannot be empty")
        if len(sample.features) != self.feature_count:
            raise ValueError(
                f"Expected {self.feature_count} features, received {len(sample.features)}"
            )
        if not all(math.isfinite(value) for value in sample.features):
            raise ValueError("Gesture features must all be finite")
