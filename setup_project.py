"""Create only safe runtime directories; never overwrite source."""

from pathlib import Path

try:
    from scripts import _bootstrap  # noqa: F401
except ModuleNotFoundError:
    import _bootstrap  # type: ignore[no-redef]  # noqa: F401

RUNTIME_DIRECTORIES = (
    "logs",
    "data/calibration",
    "output/screenshots",
    "output/recordings",
    "output/reports",
    "output/metrics",
)


def main() -> None:
    """Ensure runtime directories exist."""
    for name in RUNTIME_DIRECTORIES:
        path = Path(name)
        path.mkdir(parents=True, exist_ok=True)
        print(f"ready: {path.resolve()}")


if __name__ == "__main__":
    main()
