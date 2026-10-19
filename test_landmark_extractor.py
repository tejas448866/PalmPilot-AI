"""MediaPipe-like output extraction retains every detected hand."""

from types import SimpleNamespace

from src.hand_tracking.landmark_extractor import LandmarkExtractor


def test_both_detected_hands_are_retained() -> None:
    def raw_hand(x: float) -> SimpleNamespace:
        return SimpleNamespace(landmark=[SimpleNamespace(x=x, y=0.5) for _ in range(21)])

    def classification(label: str) -> SimpleNamespace:
        return SimpleNamespace(classification=[SimpleNamespace(label=label, score=0.9)])

    raw = SimpleNamespace(
        multi_hand_landmarks=[raw_hand(0.2), raw_hand(0.8)],
        multi_handedness=[classification("Left"), classification("Right")],
    )
    result = LandmarkExtractor().extract(raw, 1280, 720, 1.0)
    assert len(result.hands) == 2
    assert result.hands[1].landmarks.pixels[0].x == 1024
