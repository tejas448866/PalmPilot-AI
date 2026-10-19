"""Report required dependency import and version status."""

import importlib
import importlib.metadata

try:
    from scripts import _bootstrap  # noqa: F401
except ModuleNotFoundError:
    import _bootstrap  # type: ignore[no-redef]  # noqa: F401

DEPENDENCIES = {
    "cv2": "opencv-python",
    "mediapipe": "mediapipe",
    "numpy": "numpy",
    "pynput": "pynput",
    "yaml": "PyYAML",
    "dotenv": "python-dotenv",
    "PySide6": "PySide6",
}


def main() -> int:
    """Print dependency versions and return failure for missing imports."""
    missing: list[str] = []
    for module_name, package_name in DEPENDENCIES.items():
        try:
            importlib.import_module(module_name)
            print(f"OK      {package_name} {importlib.metadata.version(package_name)}")
        except (ImportError, importlib.metadata.PackageNotFoundError) as exc:
            print(f"MISSING {package_name}: {exc}")
            missing.append(package_name)
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
