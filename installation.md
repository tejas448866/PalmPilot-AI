# Windows installation

Install 64-bit Python 3.10/3.11 and VS Code, then in PowerShell:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python scripts/check_dependencies.py
```

If scripts are blocked, use `Set-ExecutionPolicy -Scope Process RemoteSigned`. Test the
webcam with `python scripts/check_camera.py --index 0`. Security software may request
camera or input-automation permission. Do not grant permissions you do not understand.
