"""Preview emergency-stop event interpretation."""


def is_stop_key(key_code: int) -> bool:
    """Return whether OpenCV key code is Q or Escape."""
    return key_code & 0xFF in (ord("q"), ord("Q"), 27)


def preview_window_closed(window_name: str) -> bool:
    """Safely determine whether an OpenCV window was closed."""
    import cv2

    try:
        return cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1
    except cv2.error:
        return False
