"""Circular angle smoothing tests."""

from src.smoothing.angle_smoothing import AngleSmoother, angular_delta


def test_angle_ema_and_wraparound() -> None:
    smoother = AngleSmoother(alpha=0.5, median_window=1)
    assert smoother.update(10) == 10
    assert smoother.update(20) == 15
    wrap = AngleSmoother(alpha=0.5, median_window=1)
    wrap.update(179)
    assert abs(angular_delta(wrap.update(-179), 180)) < 0.01


def test_median_rejects_single_spike() -> None:
    smoother = AngleSmoother(alpha=1, median_window=3)
    smoother.update(0)
    smoother.update(1)
    assert smoother.update(80) == 1
