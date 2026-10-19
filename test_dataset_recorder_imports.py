"""Regression coverage for the direct dataset-recorder entry point."""


def test_dataset_recorder_uses_production_hand_tracking_api() -> None:
    from scripts.record_gesture_dataset import build_parser
    from src.hand_tracking.hand_detector import HandDetector
    from src.hand_tracking.landmark_extractor import LandmarkExtractor

    assert build_parser().prog
    assert HandDetector.__module__ == "src.hand_tracking.hand_detector"
    assert LandmarkExtractor.__module__ == "src.hand_tracking.landmark_extractor"
