# Game plugin guide

Create `plugins/<game_id>/game.yaml`. Core code does not need registration or imports.

```yaml
game:
  id: example_game
  name: Example Game
  platform: Windows
key_mapping:
  accelerate: w
  brake: s
  left: a
  right: d
  nitro: n
sensitivity: normal
steering_limits:
  maximum_angle: 50
  dead_zone: 5
calibration:
  minimum_hand_span: 0.12
hud_branding:
  title: Example Game
  accent: "#ffb020"
```

Mappings are validated before activation. Only locally stored manifests are discovered.
Plugins contain configuration, not executable Python, which limits supply-chain risk.
