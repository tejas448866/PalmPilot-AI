# User Guide

Start with `python gui.py`. On first launch, the application selects the generic WASD
profile and Controller Test mode. Select a camera, confirm its preview, choose a profile,
and optionally run calibration. Closed fist accelerates; open palm brakes; no hand
releases pedals.

Use **Start Controller Test** before **Start Controller (LIVE)**. Live mode sends keys
to the focused application. Q, Escape, Stop Controller, Emergency Stop, window close,
Ctrl+C, camera failure, and application shutdown release tracked keys.

Profiles are keyboard templates. Verify the game's bindings and keyboard-input support.
Calibration is optional; retry any unstable stage or cancel with Q/Escape. Configuration
and first-run state are stored per user, not in packaged source files.

For CLI use:

```powershell
python scripts/check_camera.py --camera-index 0 --width 1280 --height 720
python scripts/calibrate_controller.py --force
python run.py --dry-run --calibration data/calibration/default.yaml
python run.py --live --calibration data/calibration/default.yaml
```
# Version 2 Studio workflow

Run `python gui.py`, choose **Studio Mode**, and start **Controller Test**. The left
camera card shows the real annotated controller frame, gesture, action, confidence,
tracking state, FPS, actual device resolution, and camera index. The bottom bar shows
input state only; it is not vehicle telemetry.

Racing Limits loads inside Game Workspace through Microsoft WebView2. Use **Focus** or
click the game canvas before starting LIVE input. Back, Forward, Reload, Focus,
Fullscreen, and Open Externally are available in the compact toolbar. Reloading,
leaving the Dashboard, or a browser failure safely stops active controller output.
When WebView2 Runtime is unavailable, the workspace explains why and offers the
external-browser fallback.

Controller Test is dry-run. LIVE requires confirmation. Closed fist accelerates, open
palm brakes, no hand releases, and two-hand steering is unchanged. Stop or Emergency
Stop before switching applications if there is any uncertainty.

The application requests 1280x720 but cameras may return 960x540 or 640x480. The
actual value is shown in the camera card. More pixels do not increase a camera's
physical field of view.
