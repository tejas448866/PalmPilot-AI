"""Key mapping validation."""

import pytest

from src.controller.key_mapping import validate_key_name, validate_mapping
from src.exceptions import InvalidKeyMappingError


def test_named_and_letter_keys() -> None:
    assert validate_key_name(" UP ") == "up"
    assert validate_key_name("w") == "w"
    assert (
        validate_mapping(
            {
                "accelerate": "w",
                "brake": "s",
                "left": "a",
                "right": "d",
            }
        )["left"]
        == "a"
    )


def test_invalid_key_rejected() -> None:
    with pytest.raises(InvalidKeyMappingError):
        validate_key_name("delete")
