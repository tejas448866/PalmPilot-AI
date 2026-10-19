# Windows deployment

Install development requirements, run validation, then build:

```powershell
pip install -r requirements-dev.txt
python scripts/build_release.py
python scripts/build_release.py --portable
```

PyInstaller uses `packaging/controller.spec` and bundles MediaPipe data, configuration,
plugins, and documentation. The portable command also creates a ZIP. Installer mode
uses `packaging/installer.iss` with Inno Setup after the executable is built.

Release artifacts should be code-signed by the distributor. Camera and synthetic-input
permissions may trigger endpoint-security prompts; do not weaken system security to run
the application.
