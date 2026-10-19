"""Capture labeled, deduplicated gesture features from a webcam."""

import argparse
import time
from pathlib import Path

try:
    from scripts import _bootstrap  # noqa: F401
except ModuleNotFoundError:
    import _bootstrap  # type: ignore[no-redef]  # noqa: F401

from src.camera import CameraManager, FrameProcessor, scale_preview
from src.hand_tracking.hand_detector import HandDetector
from src.hand_tracking.landmark_extractor import LandmarkExtractor
from src.ml import (
    CaptureState,
    DatasetCapturePolicy,
    GestureDataset,
    GestureSample,
    HandFeatureExtractor,
)
from src.utils.config_manager import ConfigurationManager
from src.visualization.landmark_renderer import LandmarkStyle, draw_landmarks


def build_parser() -> argparse.ArgumentParser:
    """Build the dataset-recorder CLI."""
    parser = argparse.ArgumentParser(description="Record a webcam gesture dataset")
    parser.add_argument("label", help="Gesture class label, for example open_palm")
    parser.add_argument("--sample-count", type=int, default=100)
    parser.add_argument("--countdown", type=float, default=3.0)
    parser.add_argument(
        "--capture-interval",
        type=float,
        help="Seconds between accepted samples (default: configuration value, normally 0.9)",
    )
    parser.add_argument(
        "--minimum-feature-distance",
        type=float,
        help="Minimum RMS feature change from the previous accepted pose",
    )
    parser.add_argument("--camera-index", type=int)
    parser.add_argument("--config", type=Path, default=Path("config/default_config.yaml"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/gestures.jsonl"))
    parser.add_argument("--export", type=Path)
    return parser


def main() -> int:
    """Record samples and always release OpenCV resources."""
    import cv2

    args = build_parser().parse_args()
    if not args.label.strip() or args.sample_count < 1:
        print("Label must be non-empty and counts must be positive.")
        return 1
    config = ConfigurationManager().load(args.config)
    camera_cfg, tracking_cfg = config["camera"], config["hand_tracking"]
    ml_cfg = config.get("machine_learning", {})
    capture_interval = (
        args.capture_interval
        if args.capture_interval is not None
        else float(ml_cfg.get("dataset_capture_interval_seconds", 0.9))
    )
    minimum_feature_distance = (
        args.minimum_feature_distance
        if args.minimum_feature_distance is not None
        else float(ml_cfg.get("dataset_minimum_feature_distance", 0.015))
    )
    if capture_interval < 0.1 or minimum_feature_distance < 0:
        print("Capture interval must be at least 0.1s; feature distance cannot be negative.")
        return 1
    index = args.camera_index if args.camera_index is not None else int(camera_cfg["index"])
    camera: CameraManager | None = None
    detector: HandDetector | None = None
    extractor = HandFeatureExtractor()
    dataset = GestureDataset(args.output, extractor.feature_count)
    accepted = 0
    started = time.monotonic()
    policy = DatasetCapturePolicy(capture_interval, minimum_feature_distance)
    status = "Waiting - show exactly one hand"
    accepted_feedback_until = 0.0
    try:
        camera = CameraManager(
            index,
            int(camera_cfg["requested_width"]),
            int(camera_cfg["requested_height"]),
            int(camera_cfg["fps"]),
            list(camera_cfg["backend_order"]),
            list(camera_cfg["fallback_resolutions"]),
            int(camera_cfg["processing_width"]),
            float(camera_cfg["preview_scale"]),
            int(camera_cfg["warmup_frames"]),
            camera_cfg.get("autofocus"),
            camera_cfg.get("exposure"),
        )
        flip = bool(config["accessibility"].get("mirror_mode", camera_cfg["flip_horizontal"]))
        processor = FrameProcessor(flip, camera.diagnostics.processing_resolution)
        detector = HandDetector(
            **{
                key: tracking_cfg[key]
                for key in (
                    "static_image_mode",
                    "max_num_hands",
                    "model_complexity",
                    "min_detection_confidence",
                    "min_tracking_confidence",
                )
            }
        )
        landmark_extractor = LandmarkExtractor()
        while accepted < args.sample_count:
            processed = processor.process(camera.read())
            height, width = processed.bgr.shape[:2]
            hands = landmark_extractor.extract(
                detector.process(processed.rgb), width, height, processed.timestamp
            )
            now = time.monotonic()
            remaining = max(0.0, args.countdown - (now - started))
            if remaining <= 0 and len(hands.hands) == 1:
                hand = hands.hands[0]
                features = extractor.extract(hand).values
                decision = policy.evaluate(features, now)
                if decision.ready:
                    sample = GestureSample(
                        args.label.strip(),
                        features,
                        hand.handedness,
                        processed.timestamp,
                    )
                    if dataset.append(sample):
                        policy.mark_accepted(features, now)
                        accepted += 1
                        accepted_feedback_until = now + 0.45
                        status = "Sample accepted"
                    else:
                        status = "Duplicate pose rejected - move/rotate your hand"
                elif decision.state is CaptureState.WAITING:
                    status = f"Hand detected - waiting {decision.seconds_remaining:.1f}s"
                else:
                    status = "Duplicate pose rejected - move/rotate your hand"
            elif remaining <= 0:
                status = (
                    "Waiting - show exactly one hand"
                    if not hands.hands
                    else "Waiting - exactly one hand required"
                )
            draw_landmarks(processed.bgr, hands, None, LandmarkStyle())
            headline = (
                f"Starting in {remaining:.1f}s"
                if remaining > 0
                else (
                    "Sample accepted - move/rotate your hand"
                    if now < accepted_feedback_until
                    else status
                )
            )
            messages = (
                headline,
                f"{args.label}: {accepted}/{args.sample_count}",
                "Vary rotation, distance, or finger position | Q / Esc: cancel",
            )
            for line_number, message in enumerate(messages):
                cv2.putText(
                    processed.bgr,
                    message,
                    (24, 42 + line_number * 34),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.72,
                    (255, 255, 255),
                    2,
                    cv2.LINE_AA,
                )
            cv2.imshow(
                "Gesture Dataset Recorder",
                scale_preview(processed.bgr, float(camera_cfg["preview_scale"])),
            )
            if cv2.waitKey(1) & 0xFF in (ord("q"), ord("Q"), 27):
                print("Dataset recording cancelled.")
                return 0
        report = dataset.validate({args.label.strip(): args.sample_count})
        print(f"Recorded {accepted} samples. Dataset labels: {report.labels}")
        if args.export:
            data_path, manifest_path = dataset.export(args.export)
            print(f"Exported {data_path} and {manifest_path}")
        return 0
    except KeyboardInterrupt:
        print("\nDataset recording cancelled.")
        return 0
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Dataset recording failed: {exc}")
        return 1
    finally:
        if detector:
            detector.close()
        if camera:
            camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    raise SystemExit(main())
