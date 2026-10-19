"""Resolution-aware translucent information panel."""

from typing import Any


def _rounded_panel(
    image: Any,
    top_left: tuple[int, int],
    bottom_right: tuple[int, int],
    radius: int,
    color: tuple[int, int, int],
) -> None:
    """Draw a filled rounded rectangle using inexpensive OpenCV primitives."""
    import cv2

    x1, y1 = top_left
    x2, y2 = bottom_right
    radius = min(radius, (x2 - x1) // 2, (y2 - y1) // 2)
    cv2.rectangle(image, (x1 + radius, y1), (x2 - radius, y2), color, -1)
    cv2.rectangle(image, (x1, y1 + radius), (x2, y2 - radius), color, -1)
    for center in (
        (x1 + radius, y1 + radius),
        (x2 - radius, y1 + radius),
        (x1 + radius, y2 - radius),
        (x2 - radius, y2 - radius),
    ):
        cv2.circle(image, center, radius, color, -1, cv2.LINE_AA)


def draw_status(
    frame: Any,
    lines: list[str],
    dry_run: bool,
    alpha: float = 0.55,
    ui_scale: float = 1.0,
) -> None:
    """Draw a clean alpha-blended panel with a prominent safety mode."""
    import cv2

    height, width = frame.shape[:2]
    scale = max(0.65, height / 720.0) * ui_scale
    pad = round(14 * scale)
    line_height = round(23 * scale)
    panel_width = min(width - 2 * pad, round(480 * scale))
    panel_height = pad * 2 + line_height * (len(lines) + 1)
    overlay = frame.copy()
    _rounded_panel(
        overlay,
        (pad, pad),
        (pad + panel_width, pad + panel_height),
        round(12 * scale),
        (12, 18, 25),
    )
    cv2.addWeighted(overlay, alpha, frame, 1.0 - alpha, 0, frame)
    mode_color = (40, 225, 255) if dry_run else (60, 80, 255)
    cv2.putText(
        frame,
        "DRY RUN — NO KEY OUTPUT" if dry_run else "LIVE KEYBOARD CONTROL",
        (pad * 2, pad + line_height),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.62 * scale,
        mode_color,
        max(1, round(2 * scale)),
        cv2.LINE_AA,
    )
    for index, line in enumerate(lines):
        cv2.putText(
            frame,
            line,
            (pad * 2, pad + line_height * (index + 2)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.46 * scale,
            (230, 236, 242),
            max(1, round(scale)),
            cv2.LINE_AA,
        )
