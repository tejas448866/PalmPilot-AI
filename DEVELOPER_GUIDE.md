# Developer Guide

Use Python 3.11 and install `requirements.txt` plus `requirements-dev.txt`. The pipeline
is camera → one MediaPipe inference → hand roles/features → hybrid gesture and steering
decisions → central command manager → dry-run or pynput keyboard backend. OpenCV renders
the same decision state; it does not recalculate controls.

Core invariants are dry-run by default, no simultaneous pedal conflict, release before
press on transitions, bounded frame processing, no telemetry, and unconditional cleanup.
Game additions are declarative `plugins/<id>/game.yaml` manifests. Editable user profiles
are validated and stored outside bundled resources.

Run:

```powershell
python -m pytest
python -m ruff check .
python -m black --check .
python -m mypy src
python -m compileall -q src scripts tests gui.py run.py
python -m PyInstaller --clean --noconfirm packaging/controller.spec
```
# Integrated-preview development

Keep camera/inference work out of the Qt event loop. GUI mode passes
`preview_mode="integrated"` and a frame callback into
`RacingControllerApplication`; CLI mode retains the standalone OpenCV preview.
The callback receives the same rendered frame and state used by control logic.

The Qt bridge is deliberately bounded to one pending frame. Do not replace it with an
unbounded queue. `bgr_frame_to_qimage` validates three-channel BGR input, converts once
to RGB, and calls `QImage.copy()` to detach from NumPy lifetime.

Browser integration remains optional and honest. On Windows, `auto` uses WebView2 and
falls back externally when the runtime or adapter is missing. Qt WebEngine is not a
Racing Limits candidate: diagnostic traces prove its distributed build cannot decode
the game's MP4A buffers. Keep optional browser imports lazy and store browser profiles
under the per-user application directory.

Run `pytest`, `ruff check .`, `black --check .`, `mypy src`, and compileall before a
build. Build with:

```powershell
pyinstaller --clean --noconfirm packaging/controller.spec
```
