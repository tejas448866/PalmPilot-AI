"""Central steering reference-point strategies."""

from src.utils.constants import INDEX_MCP, MIDDLE_MCP, PINKY_MCP, WRIST

from .hand_state import HandLandmarks, Point2D

RING_MCP = 13
PALM_INDICES = (WRIST, INDEX_MCP, MIDDLE_MCP, RING_MCP, PINKY_MCP)


def calculate_reference_point(landmarks: HandLandmarks, strategy: str = "palm_center") -> Point2D:
    """Calculate a normalized palm reference point."""
    if strategy == "wrist":
        return landmarks.point(WRIST)
    if strategy == "middle_mcp":
        return landmarks.point(MIDDLE_MCP)
    if strategy != "palm_center":
        raise ValueError(f"Unknown reference point strategy: {strategy}")
    points = [landmarks.point(index) for index in PALM_INDICES]
    return Point2D(
        sum(point.x for point in points) / len(points),
        sum(point.y for point in points) / len(points),
    )
