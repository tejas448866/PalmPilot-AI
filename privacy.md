# Privacy and security

All hand tracking, calibration, video recording, analytics, logging, and replay are
local. The project has no telemetry, analytics upload, cloud API, update beacon, or
automatic network-camera discovery.

DroidCam and IP Webcam are contacted only when the user explicitly supplies and enables
a URL. Use a trusted private LAN, device authentication, and a non-public URL. Session
videos and telemetry may contain sensitive imagery and behavior; protect or delete the
`output/` directory as appropriate.

Game plugins are declarative YAML and cannot execute plugin code.
