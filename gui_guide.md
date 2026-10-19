# Desktop GUI

Install requirements and run `python gui.py`. The PySide6 control center contains
Dashboard, Camera, Calibration, Profiles, Game Selection, Performance, Session Replay,
Logs, Configuration, Themes, and About tabs.

The OpenCV controller runs in a QThread, never on Qt's event loop. Profile, camera, game,
and stop requests use the thread-safe runtime settings bus and take effect without
restarting the controller. Dark, Light, Blue, Cyber, and Racing themes are local Qt
stylesheets.

The CLI remains fully supported and does not import PySide6 unless the GUI is launched.
