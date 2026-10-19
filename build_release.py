"""Build reproducible Windows executable and portable release archive."""

import argparse
import shutil
import subprocess
from pathlib import Path

try:
    from scripts import _bootstrap  # noqa: F401
except ModuleNotFoundError:
    import _bootstrap  # type: ignore[no-redef]  # noqa: F401


def main() -> int:
    """Run PyInstaller and optionally create a portable ZIP."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--portable", action="store_true")
    args = parser.parse_args()
    subprocess.run(
        ["pyinstaller", "--noconfirm", "--clean", "packaging/controller.spec"],
        check=True,
    )
    if args.portable:
        release = Path("dist/AIHandGestureRacingController-portable")
        release.mkdir(parents=True, exist_ok=True)
        executable = Path("dist/AIHandGestureRacingController.exe")
        shutil.copy2(executable, release / executable.name)
        for directory in ("config", "plugins", "docs"):
            shutil.copytree(directory, release / directory, dirs_exist_ok=True)
        shutil.make_archive(str(release), "zip", release)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
