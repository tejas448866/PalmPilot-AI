# Controls

The proposed Racing Limits mapping is Up=accelerate, Down=brake/reverse,
Left=steer left, and Right=steer right. Verify these in the current browser game;
the game can change controls independently.

Two hands form a virtual wheel. A near-horizontal line is straight; configured negative
and positive angles select left/right. Enable `steering.invert` if mirroring reverses
direction. One-hand fallback is disabled by default.

The vertical-region pedal strategy supports steering concurrently: both reference
points above `accelerate_y` accelerate, and both below `brake_y` brake. Intermediate
height is idle. Commands must persist through the configured debounce frames.

Change `key_mapping` in `config/racing_limits.yaml` to `w/s/a/d`; source edits are not
needed. The game window must have focus to receive live input.

Runtime controls:

- Q or Esc: safe shutdown
- S (P remains compatible): save a HUD screenshot
- 1: Easy steering profile
- 2: Normal steering profile
- 3: Pro steering profile
- C: next configured camera source
