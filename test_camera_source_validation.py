"""Focused validation for configured local camera indices."""

import pytest

from src.camera.camera_sources import CameraRegistry


def configured_source(source: object) -> dict[str, object]:
    """Build one enabled local-camera configuration entry."""
    return {
        "id": "test-camera",
        "name": "Test Camera",
        "kind": "local",
        "source": source,
        "enabled": True,
    }


def test_valid_integer_camera_index() -> None:
    result = CameraRegistry().configured([configured_source(2)])
    assert result[0].capture_source == 2


def test_valid_numeric_string_camera_index() -> None:
    result = CameraRegistry().configured([configured_source(" 3 ")])
    assert result[0].capture_source == 3


@pytest.mark.parametrize(
    ("source", "message"),
    [
        (None, "Camera index is required"),
        (True, "not bool"),
        (-1, "must be non-negative"),
        ("camera-zero", "non-negative integer"),
    ],
)
def test_invalid_camera_index_rejected(source: object, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        CameraRegistry().configured([configured_source(source)])
