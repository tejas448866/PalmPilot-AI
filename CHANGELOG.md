# Changelog

## 2.0.0.dev0 - Unreleased

- Integrated the existing full-resolution rendered camera stream into a large,
  aspect-preserving PySide6 dashboard through a bounded latest-frame signal.
- Added Studio, Camera Focus, and Compact Controller layouts with truthful steering,
  pedal, tracking, key, confidence, resolution, and FPS indicators.
- Added a reliable external-browser workspace with explicit launch, arrange, focus,
  and dashboard-restore controls. Optional WebEngine availability is isolated and does
  not make the application depend on embedding.
- Persisted window geometry/layout per user and extended sanitized diagnostics with
  frozen/source mode, preview mode, game integration, URL, and window state.
- Preserved the stable v1 camera, gesture, steering, calibration, command-dispatch,
  emergency-release, recording, replay, CLI, and packaging paths.

## 1.0.0 - 2026-07-27

- Finalized the local hybrid gesture controller with closed fist for acceleration,
  naturally open palm for braking, and safe release on no hand.
- Unified steering, pedals, and optional actions through the conflict-safe keyboard
  dispatcher with explicit live activation and emergency stop.
- Added full-frame multi-camera capture, calibration, recording/replay, diagnostics,
  ML dataset/training tools, game plugins, and the PySide6 control center.
- Added generic WASD and arrow-key profiles, per-user first-run settings, validated
  profile interchange, packaged-resource resolution, and sanitized diagnostics export.
- Prepared the PyInstaller release with bundled configuration, plugins, model artifacts,
  documentation, and MediaPipe resources.
