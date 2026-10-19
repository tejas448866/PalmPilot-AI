# Architecture

```text
CameraManager / MultiCameraManager
            |
       FrameProcessor
            |
 MediaPipe HandDetector (once per frame)
            |
 LandmarkExtractor + HandRoleTracker
       |                     |
 SteeringDetector      HybridGesturePolicy
       +----------+----------+
                  |
            CommandManager
                  |
     KeyboardController (dry-run/pynput)
```

The synchronous vision path is bounded and drops the concept of queued stale frames.
The PySide6 controller runs this path on a worker thread to keep Qt responsive. Abstract
commands isolate computer vision and game plugins from keyboard effects. Recording,
replay, visualization, performance, diagnostics, calibration, and ML tools consume the
same core models rather than duplicating inference.

Configuration is YAML; user state and editable profiles are stored under the operating
system's per-user application directory. `resource_path` resolves repository resources
in development and `_MEIPASS` resources in PyInstaller builds.
# Version 2 desktop studio

The production controller loop remains the single owner of capture, inference,
tracking, gestures, steering, command state, and overlay rendering. In GUI operation
it publishes the already-rendered frame and its matching runtime-state snapshot through
a Qt queued signal. The bridge permits only one pending owned frame, so slow painting
drops stale presentation frames instead of delaying control.

`src/gui/preview.py` owns BGR-to-RGB/QImage conversion and takes a safe QImage copy
before temporary NumPy storage expires. `src/gui/dashboard.py` owns presentation only.
`src/game_integration/browser_factory.py` selects the engine,
`webview2_browser.py` owns the embedded Windows child control, and
`browser_workspace.py` retains explicit external fallback operations. The GUI worker
never creates a second detector or camera.

For Racing Limits on Windows, `auto` selects WebView2 and otherwise falls back to the
external browser. Qt WebEngine remains isolated for architecture tests but is marked
unsupported for this game because its distributed codec set cannot decode the Unity
MP4A audio buffers. Browser data is stored in the per-user application directory.

Shutdown flows from Qt into the existing runtime settings bus. The production
application's `finally` path releases keys, camera, detector, recorder, and OpenCV
resources. The GUI then saves only per-user geometry and layout.
