# Calibration

Calibration accounts for camera placement, grip posture, mirroring, and comfortable
motion. Run `python scripts/calibrate_controller.py --force`. The webcam workflow
validates two-hand tracking and then collects robust sample sets for neutral, comfortable
left/right rotation, acceleration height, and brake height. Press Space to collect or
pause, R to retry a stage, Q/Esc to cancel, and S at review to save.

Median/MAD aggregation rejects unstable samples. Direction dead zone, enter/exit
hysteresis, asymmetric normalized ranges, and separated pedal thresholds are derived
and validated automatically. Results use a versioned YAML schema under
`data/calibration/` with camera modes, flip state, tracking settings, and UTC timestamp.
Existing files are protected; use `--force` intentionally to replace one.

If camera initialization fails, manual fallback is offered. Manual values must still be
explicit and valid; defaults are never silently saved.
