"""Export a bounded, sanitized local diagnostics report."""

import argparse
from pathlib import Path

from _bootstrap import bootstrap_project

bootstrap_project()

from src.diagnostics import export_diagnostics  # noqa: E402
from src.utils.file_handler import load_yaml  # noqa: E402


def main() -> int:
    """Run diagnostics export."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("config/default_config.yaml"))
    parser.add_argument("--output", type=Path, default=Path("output/diagnostics.json"))
    args = parser.parse_args()
    config = load_yaml(args.config)
    export_diagnostics(
        args.output,
        camera_config=config.get("camera", {}),
        active_profile=str(config.get("controller", {}).get("game_profile", "")),
        log_path=Path("logs/controller.log"),
    )
    print(f"Diagnostics exported to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
