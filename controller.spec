# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build definition for CLI and GUI-compatible release."""

from pathlib import Path

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
    get_package_paths,
)

project_root = Path(SPECPATH).parent
_, qtwebview2_package = get_package_paths("qtwebview2")
hiddenimports = (
    collect_submodules("mediapipe")
    + collect_submodules("pynput")
    + collect_submodules("qtwebview2")
    + [
        "src.game_integration.browser_base",
        "src.game_integration.browser_factory",
        "src.game_integration.webview2_browser",
        "src.gui.dashboard",
        "src.gui.preview",
        "src.utils.resources",
        "src.utils.user_settings",
    ]
)
datas = (
    collect_data_files("mediapipe")
    + collect_data_files("qtwebview2", includes=["lib/**"])
    + [
        # qtwebview2.utils resolves these files from _MEIPASS/lib when frozen.
        (str(Path(qtwebview2_package) / "lib"), "lib"),
        (str(project_root / "config"), "config"),
        (str(project_root / "plugins"), "plugins"),
        (str(project_root / "docs"), "docs"),
        (str(project_root / "models" / "trained"), "models/trained"),
    ]
)

analysis = Analysis(
    [str(project_root / "gui.py")],
    pathex=[str(project_root)],
    binaries=collect_dynamic_libs("qtwebview2"),
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineQuick",
        "PySide6.QtWebEngineWidgets",
    ],
    noarchive=False,
)
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name="AIHandGestureRacingController",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
