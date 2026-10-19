"""Nonblocking PySide6 desktop control center."""

import logging
import sys
import threading
import traceback
from pathlib import Path
from typing import Any

from src import __version__
from src.diagnostics import export_diagnostics
from src.game_integration import (
    BrowserState,
    BrowserWorkspaceManager,
    create_embedded_browser,
    qt_webengine_available,
    qt_webengine_version,
    select_browser_engine,
    webview2_runtime_available,
    webview2_runtime_version,
)
from src.game_profiles import GameManager
from src.main import RacingControllerApplication, load_runtime_config
from src.ml import GestureActionMapping
from src.utils.file_handler import atomic_write_text
from src.utils.logger import configure_logging, log_directory
from src.utils.resources import (
    editable_config_path,
    resource_path,
    user_config_directory,
)
from src.utils.runtime_settings import RuntimeSettings
from src.utils.user_settings import UserSettingsStore

from .themes import THEMES, stylesheet

LOGGER = logging.getLogger(__name__)


def _qt() -> dict[str, Any]:
    """Lazy-load PySide6 so CLI installations remain usable."""
    try:
        from PySide6.QtCore import QByteArray, Qt, QThread, QTimer, Signal
        from PySide6.QtWidgets import (
            QApplication,
            QComboBox,
            QHBoxLayout,
            QLabel,
            QLineEdit,
            QMainWindow,
            QMessageBox,
            QPlainTextEdit,
            QPushButton,
            QSlider,
            QSpinBox,
            QTabWidget,
            QVBoxLayout,
            QWidget,
        )
    except ImportError as exc:
        raise RuntimeError("Desktop GUI requires: pip install PySide6") from exc
    return {
        "Qt": Qt,
        "QByteArray": QByteArray,
        "QThread": QThread,
        "QTimer": QTimer,
        "Signal": Signal,
        "QApplication": QApplication,
        "QComboBox": QComboBox,
        "QHBoxLayout": QHBoxLayout,
        "QLabel": QLabel,
        "QMainWindow": QMainWindow,
        "QMessageBox": QMessageBox,
        "QLineEdit": QLineEdit,
        "QPlainTextEdit": QPlainTextEdit,
        "QPushButton": QPushButton,
        "QSpinBox": QSpinBox,
        "QSlider": QSlider,
        "QTabWidget": QTabWidget,
        "QVBoxLayout": QVBoxLayout,
        "QWidget": QWidget,
    }


def run_gui(config_path: Path | None = None) -> int:
    """Create and run the desktop GUI."""
    config_path = config_path or resource_path("config/default_config.yaml")
    qt = _qt()
    QApplication, QMainWindow = qt["QApplication"], qt["QMainWindow"]
    QWidget, QTabWidget = qt["QWidget"], qt["QTabWidget"]
    QVBoxLayout = qt["QVBoxLayout"]
    QLabel, QPushButton, QComboBox = qt["QLabel"], qt["QPushButton"], qt["QComboBox"]
    QPlainTextEdit, QSlider = qt["QPlainTextEdit"], qt["QSlider"]
    QLineEdit, QSpinBox = qt["QLineEdit"], qt["QSpinBox"]
    QThread, Signal = qt["QThread"], qt["Signal"]
    QTimer = qt["QTimer"]
    QMessageBox = qt["QMessageBox"]
    QByteArray = qt["QByteArray"]
    PremiumDashboard = __import__(
        "src.gui.dashboard", fromlist=["create_dashboard_class"]
    ).create_dashboard_class()
    ui_config = load_runtime_config(
        type(
            "UIArgs",
            (),
            {
                "config": config_path,
                "profile": resource_path("config/racing_limits.yaml"),
                "calibration": None,
                "camera_index": None,
                "dry_run": True,
                "live": False,
                "no_preview": False,
                "record": False,
                "record_session": False,
                "debug": False,
            },
        )()
    )

    settings = RuntimeSettings()
    settings_store = UserSettingsStore()
    user_settings = settings_store.load()

    class ControllerWorker(QThread):  # type: ignore[misc,valid-type]
        """Run the OpenCV controller away from the Qt event loop."""

        failed = Signal(str)
        status_changed = Signal(str)
        frame_ready = Signal(object, object)
        finished_cleanly = Signal()

        def __init__(self, dry_run: bool) -> None:
            super().__init__()
            self.dry_run = dry_run
            self._frame_pending = False
            self._frame_lock = threading.Lock()

        def publish_frame(self, frame: Any, state: dict[str, Any]) -> None:
            """Queue at most one owned frame so GUI latency cannot accumulate."""
            with self._frame_lock:
                if self._frame_pending:
                    return
                self._frame_pending = True
            self.frame_ready.emit(frame.copy(), state)

        def frame_consumed(self) -> None:
            """Allow the real-time thread to publish the next current frame."""
            with self._frame_lock:
                self._frame_pending = False

        def run(self) -> None:
            try:
                parser_args = type(
                    "Args",
                    (),
                    {
                        "config": config_path,
                        "profile": resource_path("config/racing_limits.yaml"),
                        "calibration": None,
                        "camera_index": None,
                        "dry_run": self.dry_run,
                        "live": not self.dry_run,
                        "no_preview": False,
                        "record": False,
                        "record_session": False,
                        "debug": False,
                    },
                )()
                config = load_runtime_config(parser_args)
                # Studio mode presents runtime state in native Qt controls. Keep the
                # camera image clear while retaining landmarks and steering geometry.
                config["visualization"]["draw_status"] = False
                configure_logging(
                    Path(config["logging"]["config_file"]),
                    bool(config["application"]["debug"]),
                )
                config["machine_learning"]["action_mapping"] = str(
                    editable_config_path("gesture_actions.yaml")
                )
                RacingControllerApplication(
                    config,
                    parser_args.profile,
                    runtime_settings=settings,
                    status_callback=self.status_changed.emit,
                    frame_callback=self.publish_frame,
                    preview_mode="integrated",
                ).run()
                self.finished_cleanly.emit()
            except Exception as exc:
                details = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
                LOGGER.exception("Controller preview worker failed")
                self.failed.emit(
                    "Controller Test could not start.\n\n"
                    f"{type(exc).__name__}: {exc}\n\n"
                    f"See the Logs page and {log_directory() / 'controller.log'} "
                    "for details.\n\n"
                    f"{details}"
                )

    class MainWindow(QMainWindow):  # type: ignore[misc,valid-type]
        """Tabbed desktop dashboard sharing core services with the CLI."""

        def __init__(self) -> None:
            super().__init__()
            self.worker: ControllerWorker | None = None
            self.last_runtime_state: dict[str, Any] = {}
            self.setWindowTitle(f"AI Hand Gesture Racing Controller Pro {__version__}")
            ui = ui_config["ui"]
            self.setMinimumSize(int(ui["min_window_width"]), int(ui["min_window_height"]))
            self.resize(1500, 860)
            game = ui_config["game"]
            self.workspace = BrowserWorkspaceManager(
                str(game["launch_url"]), str(game["window_title_hint"])
            )
            self.browser: Any | None = None
            self.browser_fullscreen_active = False
            self.browser_selection = select_browser_engine(
                str(game["integration_mode"]),
                str(game["preferred_embedded_engine"]),
                (
                    user_settings.last_working_browser_engine
                    if user_settings.last_working_browser_engine == "webview2"
                    else ""
                ),
                qt_webengine_available(),
                webview2_runtime_available(),
                bool(game["external_fallback_enabled"]),
            )
            self.browser_state = BrowserState(
                requested_mode=str(game["integration_mode"]),
                selected_engine=self.browser_selection.engine,
                fallback_reason=(
                    self.browser_selection.reason
                    if self.browser_selection.engine in {"external", "unavailable"}
                    else ""
                ),
            )
            tabs = QTabWidget()
            self.setCentralWidget(tabs)
            self.logs = QPlainTextEdit()
            self.logs.setReadOnly(True)
            self.controller_status = QLabel("Controller: STOPPED")
            self.dashboard = PremiumDashboard(user_settings.layout_mode)
            self.logs.appendPlainText(self.browser_selection.reason)
            tabs.addTab(self.dashboard, "Dashboard")
            self.dashboard.start_test_requested.connect(lambda: self._start(True))
            self.dashboard.start_live_requested.connect(self._start_live)
            self.dashboard.stop_requested.connect(self._stop)
            self.dashboard.emergency_requested.connect(self._emergency_stop)
            self.dashboard.launch_game_requested.connect(self._launch_game)
            self.dashboard.arrange_windows_requested.connect(self._arrange_windows)
            self.dashboard.focus_game_requested.connect(self._focus_game)
            self.dashboard.restore_dashboard_requested.connect(self._restore_dashboard)
            self.dashboard.browser_back_requested.connect(self._browser_back)
            self.dashboard.browser_forward_requested.connect(self._browser_forward)
            self.dashboard.browser_reload_requested.connect(self._browser_reload)
            self.dashboard.browser_fullscreen_requested.connect(
                lambda: self._browser_fullscreen(not self.browser_fullscreen_active)
            )
            self.dashboard.retry_embedded_requested.connect(self._initialize_browser)
            self.dashboard.layout_changed.connect(self._save_layout)
            for name in (
                "Camera",
                "Calibration",
                "Profiles",
                "Game Selection",
                "Performance",
                "Session Replay",
                "Dataset Recorder",
                "Model Training",
                "Model Evaluation",
                "Action Mapping",
                "Model Status",
                "Logs",
                "Configuration",
                "Themes",
                "About",
            ):
                tabs.addTab(self._page(name), name)
            tabs.currentChanged.connect(self._tab_changed)
            if user_settings.window_geometry:
                self.restoreGeometry(
                    QByteArray.fromBase64(user_settings.window_geometry.encode("ascii"))
                )

        def _page(self, name: str) -> Any:
            page = QWidget()
            layout = QVBoxLayout(page)
            layout.addWidget(QLabel(f"<h2>{name}</h2>"))
            if name == "Profiles":
                combo = QComboBox()
                combo.addItems(["easy", "normal", "pro"])
                combo.currentTextChanged.connect(
                    lambda value: settings.set("steering.profile", value)
                )
                layout.addWidget(combo)
            elif name == "Game Selection":
                combo = QComboBox()
                profiles = GameManager().discover()
                for profile_id, profile in profiles.items():
                    combo.addItem(profile.name, profile_id)
                selected_index = combo.findData(user_settings.selected_profile_id)
                if selected_index >= 0:
                    combo.setCurrentIndex(selected_index)
                combo.currentIndexChanged.connect(
                    lambda index: self._select_game(str(combo.itemData(index)))
                )
                layout.addWidget(combo)
            elif name == "Camera":
                layout.addWidget(QLabel(f"Selected: {user_settings.selected_camera_id}"))
                layout.addWidget(
                    QLabel(
                        "Camera health is shown in the controller preview. Start failures and "
                        "disconnects are reported explicitly and trigger safe key release."
                    )
                )
                next_camera = QPushButton("Switch to next camera")
                next_camera.clicked.connect(lambda: settings.set("camera.next", True))
                layout.addWidget(next_camera)
            elif name == "Calibration":
                layout.addWidget(
                    QLabel(
                        "Calibration is optional. The guided webcam flow measures neutral and "
                        "left/right range, hand distance, open palm, and relaxed fist."
                    )
                )
                launch = QPushButton("Start Webcam Calibration")
                launch.clicked.connect(
                    lambda: self._launch_tool(
                        "scripts/calibrate_controller.py",
                        ["--force", "--output", "data/calibration/default.yaml"],
                    )
                )
                layout.addWidget(launch)
            elif name == "Session Replay":
                slider = QSlider(qt["Qt"].Horizontal)
                layout.addWidget(QLabel("Timeline"))
                layout.addWidget(slider)
                layout.addWidget(
                    QLabel(
                        "Replay controls: pause, step, speed, and seek use the " "replay backend."
                    )
                )
            elif name == "Dataset Recorder":
                label = QLineEdit()
                label.setPlaceholderText("Gesture label (for example open_palm)")
                count = QSpinBox()
                count.setRange(10, 10000)
                count.setValue(100)
                record = QPushButton("Open Webcam Recorder")
                record.clicked.connect(
                    lambda: self._launch_tool(
                        "scripts/record_gesture_dataset.py",
                        [label.text().strip(), "--sample-count", str(count.value())],
                    )
                )
                layout.addWidget(label)
                layout.addWidget(count)
                layout.addWidget(record)
            elif name == "Model Training":
                train = QPushButton("Train and Evaluate Models")
                train.clicked.connect(
                    lambda: self._launch_tool("scripts/train_gesture_model.py", [])
                )
                layout.addWidget(train)
            elif name in {"Model Evaluation", "Model Status"}:
                artifact = (
                    Path("models/trained/gesture_model.evaluation.json")
                    if name == "Model Evaluation"
                    else Path("models/trained/gesture_model.metadata.json")
                )
                view = QPlainTextEdit()
                view.setReadOnly(True)
                refresh = QPushButton("Refresh")
                refresh.clicked.connect(
                    lambda: view.setPlainText(
                        artifact.read_text(encoding="utf-8")
                        if artifact.exists()
                        else "No trained model artifact is available."
                    )
                )
                layout.addWidget(refresh)
                layout.addWidget(view)
            elif name == "Action Mapping":
                mapping_path = editable_config_path("gesture_actions.yaml")
                layout.addWidget(
                    QLabel("Locked pedals: CLOSED FIST = ACCELERATE | OPEN PALM = BRAKE")
                )
                editor = QPlainTextEdit()
                if mapping_path.exists():
                    editor.setPlainText(mapping_path.read_text(encoding="utf-8"))
                save = QPushButton("Validate and Save Mapping")

                def save_mapping() -> None:
                    try:
                        import yaml

                        mapping = GestureActionMapping.from_mapping(
                            yaml.safe_load(editor.toPlainText())
                        )
                        mapping.validate()
                        atomic_write_text(mapping_path, editor.toPlainText())
                        self.logs.appendPlainText("Saved gesture action mapping.")
                    except (OSError, ValueError, yaml.YAMLError) as exc:
                        self.logs.appendPlainText(f"Mapping was not saved: {exc}")

                save.clicked.connect(save_mapping)
                reset = QPushButton("Reset Mapping to Defaults")

                def reset_mapping() -> None:
                    import yaml

                    defaults = resource_path("config/gesture_actions.yaml").read_text(
                        encoding="utf-8"
                    )
                    mapping = GestureActionMapping.from_mapping(yaml.safe_load(defaults))
                    mapping.save(mapping_path)
                    editor.setPlainText(defaults)
                    self.logs.appendPlainText("Gesture mapping reset to release defaults.")

                reset.clicked.connect(reset_mapping)
                layout.addWidget(editor)
                layout.addWidget(save)
                layout.addWidget(reset)
            elif name == "Themes":
                combo = QComboBox()
                combo.addItems(list(THEMES))
                combo.setCurrentText(user_settings.theme)
                combo.currentTextChanged.connect(self._select_theme)
                layout.addWidget(combo)
            elif name == "Logs":
                layout.addWidget(self.logs)
            elif name == "About":
                layout.addWidget(
                    QLabel(
                        f"Version {__version__}<br>"
                        "Privacy-first local computer vision. No telemetry, cloud service, "
                        "or automatic network discovery.<br>"
                        "Game compatibility depends on accepting keyboard input."
                    )
                )
                diagnostics = QPushButton("Export Sanitized Diagnostics")
                diagnostics.clicked.connect(self._export_diagnostics)
                layout.addWidget(diagnostics)
            else:
                layout.addWidget(QLabel("Settings update the shared runtime configuration bus."))
            layout.addStretch()
            return page

        def _launch_tool(self, script: str, arguments: list[str]) -> None:
            if not arguments or arguments[0]:
                import subprocess

                subprocess.Popen([sys.executable, script, *arguments])
            else:
                self.logs.appendPlainText("Enter a gesture label before recording.")

        def _start(self, dry_run: bool) -> None:
            if self.worker and self.worker.isRunning():
                self.logs.appendPlainText("Controller is already running.")
                return
            settings.set("shutdown_requested", False)
            settings.set("emergency_stop", False)
            settings.set("game.profile", user_settings.selected_profile_id)
            self.worker = ControllerWorker(dry_run)
            self.worker.failed.connect(self._controller_failed)
            self.worker.status_changed.connect(self._controller_status_changed)
            self.worker.frame_ready.connect(self._consume_frame)
            self.worker.finished.connect(lambda: self._controller_status_changed("stopped"))
            self.controller_status.setText(
                "Controller: TEST MODE" if dry_run else "Controller: LIVE"
            )
            self.dashboard.set_controller_mode("TEST" if dry_run else "LIVE")
            self.worker.start()

        def _consume_frame(self, frame: Any, state: dict[str, Any]) -> None:
            self.last_runtime_state = state
            self.dashboard.preview.set_frame(frame)
            self.dashboard.update_state(state)
            if self.worker:
                self.worker.frame_consumed()

        def _controller_status_changed(self, status: str) -> None:
            self.controller_status.setText(f"Controller: {status.upper()}")
            self.dashboard.set_controller_mode(status.upper())
            self.logs.appendPlainText(f"Controller: {status}")

        def _controller_failed(self, message: str) -> None:
            self.controller_status.setText("Controller: ERROR")
            self.dashboard.set_controller_mode("ERROR")
            self.logs.appendPlainText(message)
            QMessageBox.critical(self, "Controller preview failed", message)

        def _start_live(self) -> None:
            answer = QMessageBox.warning(
                self,
                "Enable live keyboard output?",
                "Live mode sends keys to the focused game. Verify test mode first. "
                "Q, Escape, Stop, and Emergency Stop release all keys.",
                QMessageBox.Yes | QMessageBox.Cancel,
                QMessageBox.Cancel,
            )
            if answer == QMessageBox.Yes:
                self._start(False)

        def _emergency_stop(self) -> None:
            settings.set("emergency_stop", True)
            self.controller_status.setText("Controller: EMERGENCY STOP")
            self.dashboard.set_controller_mode("EMERGENCY STOP")
            self.logs.appendPlainText("Emergency stop requested; releasing all keys.")

        def _stop(self) -> None:
            settings.set("shutdown_requested", True)
            self.dashboard.set_controller_mode("STOPPING")

        def _launch_game(self) -> None:
            try:
                status = self.workspace.launch()
                display_status = "Browser launched"
            except (OSError, RuntimeError, ValueError) as exc:
                status = f"Game launch failed: {exc}"
                display_status = "Not launched"
            self.dashboard.game_status.setText(display_status)
            self.logs.appendPlainText(status)

        def _initialize_browser(self) -> None:
            if self.browser:
                self.browser.load_url(self.workspace.game_url)
                return
            if self.browser_selection.engine not in {"qt_webengine", "webview2"}:
                self.dashboard.show_browser_error(self.browser_selection.reason)
                return
            try:
                self.browser = create_embedded_browser(
                    self.browser_selection,
                    self.dashboard.browser_host,
                    str(ui_config["game"]["integration_mode"]),
                    user_config_directory() / "browser" / self.browser_selection.engine,
                    bool(ui_config["game"]["allow_fullscreen"]),
                )
                self.browser.state_changed.connect(self._browser_state_changed)
                self.browser.navigation_started.connect(self._browser_navigation_started)
                self.browser.fullscreen_requested.connect(self._browser_fullscreen)
                self.browser.crashed.connect(self._browser_crashed)
                self.dashboard.set_browser_widget(self.browser.widget, self.browser.engine_name())
                self.browser.load_url(self.workspace.game_url)
            except (ImportError, OSError, RuntimeError) as exc:
                LOGGER.exception("Embedded browser initialization failed")
                self.browser_state.last_error = str(exc)
                self.browser_state.fallback_reason = str(exc)
                self.dashboard.show_browser_error(str(exc))
                self.logs.appendPlainText(f"Embedded browser unavailable: {exc}")

        def _browser_state_changed(self, state: BrowserState) -> None:
            self.browser_state = state
            self.dashboard.update_browser_state(state)

        def _browser_navigation_started(self, _url: str) -> None:
            self._release_for_browser_event("browser navigation")

        def _browser_back(self) -> None:
            if self.browser:
                self.browser.go_back()

        def _browser_forward(self) -> None:
            if self.browser:
                self.browser.go_forward()

        def _browser_reload(self) -> None:
            self._release_for_browser_event("browser reload")
            if self.browser:
                self.browser.reload()

        def _browser_fullscreen(self, enabled: bool) -> None:
            if not bool(ui_config["game"]["allow_fullscreen"]):
                return
            if enabled:
                self.showFullScreen()
            else:
                self.showNormal()
            self.browser_fullscreen_active = enabled
            if self.browser:
                self.browser.focus_game()

        def _browser_crashed(self, message: str) -> None:
            self.logs.appendPlainText(message)
            self._release_for_browser_event("browser crash", emergency=True)
            self.dashboard.show_browser_error(message)

        def _release_for_browser_event(self, reason: str, *, emergency: bool = False) -> None:
            """Stop the controller so its command manager releases every key."""
            if not self.worker or not self.worker.isRunning():
                return
            settings.set("emergency_stop" if emergency else "shutdown_requested", True)
            self.dashboard.set_controller_mode("EMERGENCY STOP" if emergency else "STOPPING")
            self.logs.appendPlainText(
                f"Controller stopped for {reason}; releasing all synthetic keys."
            )

        def _tab_changed(self, index: int) -> None:
            if index != 0 and self.worker and self.worker.isRunning():
                self._release_for_browser_event("Dashboard tab leave")

        def _arrange_windows(self) -> None:
            status = self.workspace.arrange(int(self.winId()))
            display_status = (
                "Arrangement ready"
                if "side by side" in status
                else "Window not detected" if "not found" in status else "Not launched"
            )
            self.dashboard.game_status.setText(display_status)
            self.logs.appendPlainText(status)

        def _focus_game(self) -> None:
            if self.browser:
                self.browser.focus_game()
                status = "Game focused"
                self.dashboard.game_status.setText(status)
            else:
                status = self.workspace.focus_game()
                self.dashboard.game_status.setText(
                    "Game focused" if status == "Game focused" else "Window not detected"
                )
            self.logs.appendPlainText(status)

        def _restore_dashboard(self) -> None:
            self.showNormal()
            self.raise_()
            self.activateWindow()

        def _save_layout(self, value: str) -> None:
            user_settings.layout_mode = value
            settings_store.save(user_settings)

        def _select_game(self, profile_id: str) -> None:
            user_settings.selected_profile_id = profile_id
            settings_store.save(user_settings)
            settings.set("game.profile", profile_id)

        def _select_theme(self, value: str) -> None:
            QApplication.instance().setStyleSheet(stylesheet(value))
            user_settings.theme = value
            settings_store.save(user_settings)

        def _export_diagnostics(self) -> None:
            import cv2
            import PySide6

            screen = QApplication.primaryScreen()
            screen_size = [screen.size().width(), screen.size().height()] if screen else []
            output = Path("output/diagnostics.json")
            export_diagnostics(
                output,
                {
                    "selected_camera_id": user_settings.selected_camera_id,
                    "requested_resolution": (
                        ui_config["camera"]["requested_width"],
                        ui_config["camera"]["requested_height"],
                    ),
                    "actual_resolution": self.last_runtime_state.get("actual_resolution", ()),
                    "fps": self.last_runtime_state.get("fps", 0.0),
                    "backend": self.last_runtime_state.get("camera_backend", "unavailable"),
                },
                user_settings.selected_profile_id,
                Path("logs/controller.log"),
                runtime_context={
                    "preview_rendering_mode": "integrated_qt",
                    "selected_layout_mode": user_settings.layout_mode,
                    "game_integration_mode": self.browser_state.requested_mode,
                    "embedded_browser_available": webview2_runtime_available(),
                    "qt_webengine_version": qt_webengine_version(),
                    "webview2_runtime_available": webview2_runtime_available(),
                    "webview2_runtime_version": webview2_runtime_version(),
                    "external_window_detected": self.workspace.game_handle is not None,
                    "active_game_url": self.workspace.game_url,
                    "application_window_geometry": [
                        self.x(),
                        self.y(),
                        self.width(),
                        self.height(),
                    ],
                    "qt_pyside_version": PySide6.__version__,
                    "opencv_version": cv2.__version__,
                    "screen_resolution": screen_size,
                }
                | self.browser_state.diagnostics(),
            )
            self.logs.appendPlainText(f"Diagnostics exported to {output}")

        def closeEvent(self, event: Any) -> None:
            settings.set("emergency_stop", True)
            user_settings.window_geometry = bytes(self.saveGeometry().toBase64()).decode("ascii")
            settings_store.save(user_settings)
            if self.worker:
                self.worker.wait(3000)
            self._shutdown_browser()
            event.accept()

        def _shutdown_browser(self) -> None:
            self._release_for_browser_event("browser shutdown")
            if self.browser:
                try:
                    self.browser.shutdown()
                except RuntimeError:
                    LOGGER.exception("Embedded browser shutdown failed")
                self.browser = None

    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(stylesheet(user_settings.theme))
    window = MainWindow()
    window.show()
    QTimer.singleShot(250, window._initialize_browser)
    if not user_settings.first_run_completed:
        QMessageBox.information(
            window,
            "Welcome",
            "A safe Generic WASD profile and controller test mode are selected. "
            "Closed fist accelerates; open palm brakes; removing your hand releases controls. "
            "Calibration is optional.",
        )
        user_settings.first_run_completed = True
        settings_store.save(user_settings)
    return int(app.exec())
