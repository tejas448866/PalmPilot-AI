"""Calibration resource cleanup without webcam or GUI."""

from types import SimpleNamespace

from scripts.calibrate_controller import WebcamCalibrationSession


def test_calibration_cleanup_releases_all(monkeypatch) -> None:
    calls: list[str] = []
    fake_cv2 = SimpleNamespace(destroyAllWindows=lambda: calls.append("windows"))
    monkeypatch.setitem(__import__("sys").modules, "cv2", fake_cv2)
    session = WebcamCalibrationSession.__new__(WebcamCalibrationSession)
    session.keyboard = SimpleNamespace(release_all=lambda: calls.append("keys"))
    session.detector = SimpleNamespace(close=lambda: calls.append("detector"))
    session.camera = SimpleNamespace(release=lambda: calls.append("camera"))
    session.close()
    assert calls == ["keys", "detector", "camera", "windows"]
