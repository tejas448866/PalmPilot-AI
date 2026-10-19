"""Full-frame camera negotiation and preview diagnostic."""

import argparse
from pathlib import Path

try:
    from scripts import _bootstrap  # noqa: F401
except ModuleNotFoundError:
    import _bootstrap  # type: ignore[no-redef]  # noqa: F401

from src.camera import CameraManager, FrameProcessor, scale_preview
from src.exceptions import CameraError
from src.utils.config_manager import ConfigurationManager


def main() -> int:
    """Open a negotiated camera mode and exit normally on user cancellation."""
    import cv2

    parser = argparse.ArgumentParser(description="Check full-frame webcam capture")
    parser.add_argument("--camera-index", "--index", dest="camera_index", type=int, default=0)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--preview-scale", type=float, default=1.0)
    parser.add_argument("--config", type=Path, default=Path("config/default_config.yaml"))
    args = parser.parse_args()
    config = ConfigurationManager().load(args.config)
    flip_horizontal = bool(
        config["accessibility"].get(
            "mirror_mode",
            config["camera"]["flip_horizontal"],
        )
    )
    frame_processor = FrameProcessor(flip_horizontal=flip_horizontal)
    camera: CameraManager | None = None
    try:
        camera = CameraManager(
            args.camera_index,
            args.width,
            args.height,
            30,
            ["dshow", "msmf", "default"],
            [[960, 540], [640, 480]],
            preview_scale=args.preview_scale,
            warmup_frames=15,
        )
        details = camera.diagnostics
        print(f"Camera index: {details.index}")
        print(f"Backend: {details.backend}")
        print(f"Requested resolution: {details.requested_resolution}")
        print(f"Negotiated resolution: {details.negotiated_resolution}")
        print(f"Actual resolution: {details.actual_resolution}")
        print(f"Preview resolution: {details.preview_resolution}")
        print("The preview is resized only; it is not cropped. Press Q or Esc to quit.")
        while True:
            frame = frame_processor.process(camera.read()).bgr
            cv2.imshow("Full-frame camera check", scale_preview(frame, args.preview_scale))
            if cv2.waitKey(1) & 0xFF in (ord("q"), ord("Q"), 27):
                return 0
    except KeyboardInterrupt:
        print("\nCamera check cancelled.")
        return 0
    except CameraError as exc:
        print(f"Camera error: {exc}")
        return 1
    finally:
        if camera:
            camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    raise SystemExit(main())
