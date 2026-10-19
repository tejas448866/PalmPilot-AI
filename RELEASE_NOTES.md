# AI Hand Gesture Racing Controller

## 2.0.0.dev0 - Unreleased

This development release introduces the premium desktop studio without replacing the
stable v1 controller. The camera still targets 1280x720 and gracefully negotiates
fallbacks, but the GUI now presents the existing annotated frame in a large, smooth,
aspect-correct Qt panel. No duplicate landmark inference is performed.

The right-hand workspace launches the configured game in the system browser and can
arrange the dashboard and browser side by side on Windows. Direct Qt WebEngine
embedding is not enabled by default because third-party Unity/WebGL behavior cannot be
guaranteed across audio, focus, fullscreen, storage, browser compatibility, and site
policy changes.

This is not a tagged release. Stable v1.0.0 remains available as tag `v1.0.0`.

## 1.0.0 - Stable

This is the stable production release. It is a local, privacy-first computer-vision
input controller; it does not automate gameplay or bypass anti-cheat systems.

The default pedal contract is final: a relaxed closed fist accelerates, a naturally
open palm brakes, and removing the hand releases pedal keys. Dry-run/test mode is the
default. Live keyboard output requires explicit activation.

Game profiles are keyboard templates. Compatibility depends on the game accepting the
configured keyboard inputs and must be verified by the user. Webcam quality, physical
field of view, lighting, occlusion, browser focus, and game input policy remain
hardware/environment limitations.

Recommended release tag: `v1.0.0`. No tag or remote release is created automatically.
