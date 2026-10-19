"""Premium controller dashboard composed from reusable Qt widgets."""

from typing import Any


def create_dashboard_class() -> type:
    """Create the dashboard lazily so non-GUI commands remain lightweight."""
    from PySide6.QtCore import Qt, QTimer, Signal
    from PySide6.QtGui import QColor, QPainter, QPen
    from PySide6.QtWidgets import (
        QComboBox,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QLabel,
        QProgressBar,
        QPushButton,
        QSizePolicy,
        QSplitter,
        QStackedWidget,
        QVBoxLayout,
        QWidget,
    )

    CameraPreview = __import__(
        "src.gui.preview", fromlist=["create_camera_preview_class"]
    ).create_camera_preview_class()

    class SteeringGauge(QWidget):
        """Small truthful input gauge driven by normalized steering state."""

        def __init__(self) -> None:
            super().__init__()
            self.value = 0.0
            self.setFixedSize(92, 48)

        def set_value(self, value: float) -> None:
            self.value = max(-1.0, min(1.0, value))
            self.update()

        def paintEvent(self, _event: Any) -> None:
            import math

            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            center_x, center_y = self.width() / 2, self.height() * 0.65
            radius = min(self.width() * 0.28, self.height() * 0.38)
            painter.setPen(QPen(QColor("#697386"), 5))
            painter.drawEllipse(
                int(center_x - radius),
                int(center_y - radius),
                int(radius * 2),
                int(radius * 2),
            )
            angle = math.radians(-90 + self.value * 70)
            end_x = center_x + math.cos(angle) * radius * 0.78
            end_y = center_y + math.sin(angle) * radius * 0.78
            painter.setPen(QPen(QColor("#ffb020"), 5))
            painter.drawLine(int(center_x), int(center_y), int(end_x), int(end_y))

    class PremiumDashboard(QWidget):
        """Camera studio, external-game workspace, and live input state."""

        start_test_requested = Signal()
        start_live_requested = Signal()
        stop_requested = Signal()
        emergency_requested = Signal()
        launch_game_requested = Signal()
        arrange_windows_requested = Signal()
        focus_game_requested = Signal()
        restore_dashboard_requested = Signal()
        browser_back_requested = Signal()
        browser_forward_requested = Signal()
        browser_reload_requested = Signal()
        browser_fullscreen_requested = Signal()
        retry_embedded_requested = Signal()
        layout_changed = Signal(str)

        def __init__(self, layout_mode: str = "studio") -> None:
            super().__init__()
            self._initial_split_applied = False
            root = QVBoxLayout(self)
            root.setContentsMargins(18, 14, 18, 14)
            root.setSpacing(12)

            header = QHBoxLayout()
            title = QLabel("AI Hand Gesture Racing Controller Pro")
            title.setObjectName("productTitle")
            self.mode_badge = QLabel("STOPPED")
            self.mode_badge.setObjectName("modeBadge")
            self.layout_combo = QComboBox()
            self.layout_combo.addItem("Studio Mode", "studio")
            self.layout_combo.addItem("Camera Focus", "camera_focus")
            self.layout_combo.addItem("Compact Controller", "compact")
            selected = self.layout_combo.findData(layout_mode)
            self.layout_combo.setCurrentIndex(max(0, selected))
            self.layout_combo.currentIndexChanged.connect(
                lambda index: self._set_layout(str(self.layout_combo.itemData(index)))
            )
            header.addWidget(title)
            header.addStretch()
            header.addWidget(QLabel("Layout"))
            header.addWidget(self.layout_combo)
            header.addWidget(self.mode_badge)
            root.addLayout(header)

            self.splitter = QSplitter(Qt.Orientation.Horizontal)
            self.camera_card = self._card("CAMERA & HAND TRACKING")
            camera_layout = self.camera_card.layout()
            self.preview = CameraPreview()
            camera_layout.addWidget(
                self.preview,
                0,
                Qt.AlignmentFlag.AlignTop,
            )
            camera_layout.addStretch()
            self.tracking = QLabel("LOST")
            self.fps = QLabel("0.0 FPS")

            self.game_card = self._card("GAME WORKSPACE")
            game_layout = self.game_card.layout()
            browser_toolbar = QHBoxLayout()
            browser_toolbar.setContentsMargins(0, 0, 0, 0)
            browser_toolbar.setSpacing(4)
            for text, signal in (
                ("Back", self.browser_back_requested),
                ("Forward", self.browser_forward_requested),
                ("Reload", self.browser_reload_requested),
                ("Focus", self.focus_game_requested),
                ("Fullscreen", self.browser_fullscreen_requested),
                ("Open External", self.launch_game_requested),
            ):
                button = QPushButton(text)
                button.setObjectName("browserToolButton")
                button.setMinimumWidth(0)
                button.setMaximumWidth(90)
                button.clicked.connect(signal.emit)
                browser_toolbar.addWidget(button)
            self.browser_engine = QLabel("Embedded browser not initialized")
            self.browser_engine.setObjectName("browserEngine")
            self.browser_engine.setMaximumWidth(120)
            browser_toolbar.addStretch()
            browser_toolbar.addWidget(self.browser_engine)
            game_layout.addLayout(browser_toolbar)
            self.load_progress = QProgressBar()
            self.load_progress.setRange(0, 100)
            self.load_progress.setTextVisible(False)
            self.load_progress.setMaximumHeight(3)
            self.load_progress.hide()
            game_layout.addWidget(self.load_progress)

            self.game_stack = QStackedWidget()
            self.game_placeholder = QWidget()
            placeholder_layout = QVBoxLayout(self.game_placeholder)
            game_title = QLabel("Racing Limits")
            game_title.setObjectName("gameTitle")
            game_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.game_status = QLabel("Ready to load inside the dashboard")
            self.game_status.setObjectName("gameStatus")
            self.game_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.game_status.setWordWrap(True)
            launch_embedded = QPushButton("Launch Game")
            launch_embedded.clicked.connect(self.retry_embedded_requested.emit)
            placeholder_layout.addStretch()
            placeholder_layout.addWidget(game_title)
            placeholder_layout.addWidget(self.game_status)
            placeholder_layout.addWidget(launch_embedded, 0, Qt.AlignmentFlag.AlignHCenter)
            placeholder_layout.addStretch()

            self.browser_host = QWidget()
            self.browser_host_layout = QVBoxLayout(self.browser_host)
            self.browser_host_layout.setContentsMargins(0, 0, 0, 0)
            self.browser_host_layout.setSpacing(0)

            self.browser_error = QWidget()
            error_layout = QVBoxLayout(self.browser_error)
            self.browser_error_text = QLabel("Embedded game unavailable")
            self.browser_error_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.browser_error_text.setWordWrap(True)
            error_buttons = QHBoxLayout()
            retry = QPushButton("Retry embedded mode")
            retry.clicked.connect(self.retry_embedded_requested.emit)
            external = QPushButton("Open externally")
            external.clicked.connect(self.launch_game_requested.emit)
            for button in (retry, external):
                error_buttons.addWidget(button)
            error_layout.addStretch()
            error_layout.addWidget(self.browser_error_text)
            error_layout.addLayout(error_buttons)
            error_layout.addStretch()

            self.game_stack.addWidget(self.game_placeholder)
            self.game_stack.addWidget(self.browser_host)
            self.game_stack.addWidget(self.browser_error)
            game_layout.addWidget(self.game_stack, 1)

            fallback_container = QWidget()
            fallback_buttons = QGridLayout(fallback_container)
            fallback_buttons.setContentsMargins(0, 0, 0, 0)
            for row, column, text, signal in (
                (0, 0, "Arrange Windows", self.arrange_windows_requested),
                (0, 1, "Restore Dashboard", self.restore_dashboard_requested),
            ):
                button = QPushButton(text)
                button.setObjectName("externalFallbackButton")
                button.clicked.connect(signal.emit)
                fallback_buttons.addWidget(button, row, column)
            self.external_window_controls = fallback_container
            game_layout.addWidget(fallback_container)

            self.splitter.addWidget(self.camera_card)
            self.splitter.addWidget(self.game_card)
            self.splitter.setChildrenCollapsible(False)
            self.splitter.setStretchFactor(0, 41)
            self.splitter.setStretchFactor(1, 59)
            root.addWidget(self.splitter, 1)

            state_card = QFrame()
            state_card.setObjectName("stateBar")
            state_card.setMaximumHeight(64)
            state_layout = QHBoxLayout(state_card)
            state_layout.setContentsMargins(8, 4, 8, 4)
            state_layout.setSpacing(7)
            self.steering_gauge = SteeringGauge()
            self.steering_label = QLabel("STEERING: NEUTRAL")
            self.accelerate = QLabel("ACCELERATE OFF")
            self.brake = QLabel("BRAKE OFF")
            self.keys = QLabel("KEYS: -")
            self.controller = QLabel("CONTROLLER STOPPED")
            state_layout.addWidget(self.steering_gauge)
            for widget in (
                self.steering_label,
                self.accelerate,
                self.brake,
                self.tracking,
                self.fps,
                self.keys,
                self.controller,
            ):
                widget.setObjectName("stateChip")
                state_layout.addWidget(widget)
            state_layout.addStretch()
            root.addWidget(state_card)

            controls = QHBoxLayout()
            controls.setSpacing(8)
            for text, name, signal in (
                ("Controller Test", "secondaryButton", self.start_test_requested),
                ("Start LIVE", "primaryButton", self.start_live_requested),
                ("Stop", "secondaryButton", self.stop_requested),
                ("EMERGENCY STOP", "dangerButton", self.emergency_requested),
            ):
                button = QPushButton(text)
                button.setObjectName(name)
                button.setMinimumHeight(34)
                button.setMaximumHeight(38)
                button.clicked.connect(signal.emit)
                controls.addWidget(button)
            root.addLayout(controls)
            self._set_layout(layout_mode)

        def showEvent(self, event: Any) -> None:
            super().showEvent(event)
            if not self._initial_split_applied:
                self._initial_split_applied = True
                mode = str(self.layout_combo.currentData())
                QTimer.singleShot(0, lambda: self._set_layout(mode))

        @staticmethod
        def _card(title: str) -> Any:
            frame = QFrame()
            frame.setObjectName("dashboardCard")
            frame.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
            layout = QVBoxLayout(frame)
            layout.setContentsMargins(10, 7, 10, 10)
            layout.setSpacing(6)
            heading = QLabel(title)
            heading.setObjectName("cardTitle")
            layout.addWidget(heading)
            return frame

        def _set_layout(self, mode: str) -> None:
            self.camera_card.setVisible(True)
            self.game_card.setVisible(mode != "camera_focus")
            if mode == "studio":
                self.splitter.setSizes([410, 590])
            elif mode == "camera_focus":
                self.splitter.setSizes([1200, 0])
            else:
                self.splitter.setSizes([430, 760])
            self.layout_changed.emit(mode)

        def update_state(self, state: dict[str, Any]) -> None:
            """Render state produced by the real controller pipeline."""
            tracking = bool(state.get("tracking", False))
            steering = float(state.get("steering_value", 0.0))
            steering_command = str(state.get("steering_command", "straight")).upper()
            pedal = str(state.get("pedal", "idle"))
            keys = tuple(state.get("active_keys", ()))
            self.tracking.setText("LIVE" if tracking else "LOST")
            self.fps.setText(f"{float(state.get('fps', 0.0)):.1f} FPS")
            self.steering_gauge.set_value(steering)
            self.steering_label.setText(f"STEERING: {steering_command}")
            self.accelerate.setText("ACCELERATE ON" if pedal == "accelerate" else "ACCELERATE OFF")
            self.brake.setText("BRAKE ON" if pedal == "brake" else "BRAKE OFF")
            self.keys.setText("KEYS: " + (" / ".join(keys).upper() if keys else "-"))

        def set_controller_mode(self, text: str) -> None:
            self.mode_badge.setText(text)
            self.controller.setText(f"CONTROLLER {text}")
            self.preview.set_mode(text)

        def set_browser_widget(self, widget: Any, engine_name: str) -> None:
            """Replace the placeholder with a genuinely embedded browser widget."""
            while self.browser_host_layout.count():
                item = self.browser_host_layout.takeAt(0)
                old_widget = item.widget() if item else None
                if old_widget and old_widget is not widget:
                    old_widget.setParent(None)
            self.browser_host_layout.addWidget(widget)
            self.browser_engine.setText(engine_name)
            self.external_window_controls.hide()
            self.game_stack.setCurrentWidget(self.browser_host)

        def update_browser_state(self, state: Any) -> None:
            """Present loading state without covering browser content."""
            loading = str(getattr(state.loading_state, "value", state.loading_state))
            engine = str(state.selected_engine)
            self.browser_engine.setText(
                "Microsoft WebView2" if engine == "webview2" else engine.replace("_", " ").title()
            )
            self.load_progress.setValue(int(state.load_progress))
            self.load_progress.setVisible(loading == "loading")
            if loading in {"failed", "crashed"}:
                self.show_browser_error(state.last_error or "Embedded game unavailable")
            elif loading == "loaded":
                self.game_stack.setCurrentWidget(self.browser_host)

        def show_browser_error(self, reason: str) -> None:
            self.browser_error_text.setText(f"Embedded game unavailable\n\nReason: {reason}")
            self.external_window_controls.show()
            self.game_stack.setCurrentWidget(self.browser_error)

    return PremiumDashboard
