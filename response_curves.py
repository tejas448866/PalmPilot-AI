"""Continuous steering response curves."""

import math

from src.utils.geometry import clamp


def apply_response_curve(value: float, curve: str, strength: float = 2.0) -> float:
    """Map normalized steering while preserving sign and endpoints."""
    value = clamp(value, -1.0, 1.0)
    magnitude = abs(value)
    name = curve.lower()
    if name == "linear":
        mapped = magnitude
    elif name == "cubic":
        mapped = magnitude**3
    elif name == "exponential":
        if strength <= 0:
            raise ValueError("exponential strength must be positive")
        mapped = math.expm1(strength * magnitude) / math.expm1(strength)
    elif name == "sigmoid":
        if strength <= 0:
            raise ValueError("sigmoid strength must be positive")
        raw = 1.0 / (1.0 + math.exp(-strength * (magnitude - 0.5)))
        low = 1.0 / (1.0 + math.exp(strength * 0.5))
        high = 1.0 / (1.0 + math.exp(-strength * 0.5))
        mapped = (raw - low) / (high - low)
    else:
        raise ValueError(f"Unsupported steering response curve: {curve}")
    return math.copysign(mapped, value)
