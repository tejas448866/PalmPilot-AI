"""Script-compatible launcher without duplicated business logic."""

try:
    from scripts import _bootstrap  # noqa: F401
except ModuleNotFoundError:
    import _bootstrap  # type: ignore[no-redef]  # noqa: F401

from src.main import main

if __name__ == "__main__":
    raise SystemExit(main())
