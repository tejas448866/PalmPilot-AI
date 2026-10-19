"""Pure stylesheet theme engine."""

THEMES: dict[str, dict[str, str]] = {
    "Dark": {"background": "#17191f", "panel": "#23262f", "text": "#f0f2f5", "accent": "#ffb020"},
    "Light": {"background": "#f2f4f7", "panel": "#ffffff", "text": "#20242b", "accent": "#d97800"},
    "Blue": {"background": "#101b2d", "panel": "#172b46", "text": "#edf6ff", "accent": "#36a8ff"},
    "Cyber": {"background": "#090d13", "panel": "#111a24", "text": "#dffcff", "accent": "#00f5d4"},
    "Racing": {"background": "#130f10", "panel": "#24191b", "text": "#fff4f4", "accent": "#ef3340"},
}


def stylesheet(theme_name: str) -> str:
    """Return a syntactically valid, contrast-safe Qt stylesheet."""
    theme = THEMES[theme_name]
    background = theme["background"]
    panel = theme["panel"]
    text = theme["text"]
    accent = theme["accent"]
    return f"""
QWidget {{
    background-color: {background};
    color: {text};
    font-family: "Segoe UI";
}}
QMainWindow, QTabWidget::pane {{
    background-color: {background};
}}
QLabel, QCheckBox, QRadioButton, QGroupBox {{
    color: {text};
    background-color: transparent;
}}
QTabWidget::pane {{
    border: 1px solid #3a3f4b;
}}
QTabBar::tab {{
    background-color: {panel};
    color: {text};
    border: 1px solid #3a3f4b;
    padding: 8px 12px;
}}
QTabBar::tab:selected {{
    background-color: {accent};
    color: #101216;
}}
QGroupBox, QFrame#card, QFrame#dashboardCard, QFrame#stateBar {{
    background-color: {panel};
    border: 1px solid #3a3f4b;
    border-radius: 8px;
    margin: 0;
    padding: 0;
}}
QLabel#productTitle {{
    font-size: 22px;
    font-weight: 700;
}}
QLabel#cardTitle {{
    font-size: 12px;
    font-weight: 600;
    color: {accent};
    padding: 0;
    margin: 0;
}}
QLabel#cameraPreview {{
    background-color: #080a0e;
    border: 1px solid #3a3f4b;
    border-radius: 6px;
}}
QLabel#previewModeBadge {{
    background-color: rgba(15, 18, 24, 90);
    color: #ffffff;
    border: 1px solid rgba(255, 255, 255, 45);
    border-radius: 5px;
    padding: 4px 7px;
    font-size: 10px;
    font-weight: 600;
}}
QLabel#gameTitle {{
    font-size: 22px;
    font-weight: 650;
}}
QLabel#gameStatus {{
    color: #aeb5c0;
    font-size: 13px;
}}
QLabel#stateChip {{
    background-color: rgba(255, 255, 255, 12);
    border: 1px solid #3a3f4b;
    border-radius: 5px;
    padding: 5px 7px;
    font-size: 11px;
    font-weight: 600;
}}
QPushButton#dangerButton {{
    background-color: #c9343b;
    color: #ffffff;
}}
QPushButton {{
    background-color: {accent};
    color: #101216;
    border: none;
    border-radius: 6px;
    padding: 8px 14px;
    font-weight: bold;
}}
QPushButton:hover {{
    border: 1px solid {text};
}}
QPushButton:disabled {{
    background-color: #555b65;
    color: #d8dbe0;
}}
QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit, QPlainTextEdit,
QTextEdit, QListView, QTreeView, QTableView, QTableWidget {{
    background-color: {panel};
    color: {text};
    border: 1px solid #555b65;
    border-radius: 5px;
    padding: 6px;
    selection-background-color: {accent};
    selection-color: #101216;
}}
QComboBox QAbstractItemView {{
    background-color: {panel};
    color: {text};
    selection-background-color: {accent};
    selection-color: #101216;
}}
QHeaderView::section {{
    background-color: {panel};
    color: {text};
    border: 1px solid #555b65;
    padding: 6px;
}}
QToolTip {{
    background-color: {panel};
    color: {text};
    border: 1px solid {accent};
}}
QSlider::groove:horizontal {{
    height: 6px;
    background-color: #454b56;
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    width: 16px;
    background-color: {accent};
    margin: -5px 0;
    border-radius: 8px;
}}
"""
