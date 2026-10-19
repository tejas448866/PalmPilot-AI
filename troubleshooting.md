# Troubleshooting

- **Camera will not start:** run `scripts/check_camera.py`, try another configured
  backend/source, close software already using the camera, and inspect logs.
- **Black preview:** select another source; camera failures are reported rather than
  treated as valid frames.
- **One hand or flickering:** use even front lighting, a contrasting background, keep
  the whole hand visible, and avoid overlap.
- **Preview seems zoomed:** software preserves the complete negotiated frame and aspect
  ratio but cannot increase optical field of view. Higher resolution does not guarantee
  wider FOV.
- **Low FPS:** reduce processing width or use frame skipping conservatively; do not
  trade away recognition reliability merely for a higher counter.
- **Gestures fail:** verify closed fist/open palm in dry-run, then tune normalized hybrid
  thresholds or use optional calibration.
- **Keys do not affect a game:** focus the game and verify its keyboard bindings/input
  policy. Compatibility is not guaranteed.
- **Emergency:** press Q/Escape or the GUI Emergency Stop button, then close the app.
# Version 2 desktop troubleshooting

## Camera panel is blank

Start Controller Test and read the concise GUI error. Check the rotating controller
log for the full traceback. Confirm no other application owns the camera, then stop
and restart. The camera card reports the actual negotiated resolution; unsupported
1280x720 automatically falls back.

## Preview looks soft, cropped, or stretched

Qt preserves aspect ratio and uses smooth display scaling. The capture remains at the
device's negotiated resolution even when the widget is smaller. Software cannot widen
physical optical field of view. Disable any vendor digital-zoom utility and consider a
wide-angle external camera when both hands cannot fit.

## Game does not receive input

Controller Test never sends keys. Confirm LIVE mode, use **Focus**, or click the
embedded game canvas. Verify W/A/S/D in the game's tutorial. The application does not
bypass browser or game input policies.

## Embedded game unavailable

Install the official Microsoft WebView2 Runtime and the project's optional
`qtwebview2` dependency, then retry. The application never installs either silently.
Use **Open Externally** when embedding remains unavailable. Qt WebEngine is deliberately
not offered for Racing Limits because its MP4A decode failure terminates the Unity game.

## Stuck-key concern

Press Emergency Stop immediately. Stop, Q/Escape in standalone preview, camera
failure, tracking loss, and normal application shutdown route through the existing
central release policy. If Windows terminates the process forcibly, release behavior
cannot be guaranteed.
