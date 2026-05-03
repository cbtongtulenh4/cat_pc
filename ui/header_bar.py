"""
Header Bar — Top bar with app logo.
Windows 11 Fluent Design style with clean, minimal appearance.
"""
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt
from ui.theme import Colors


class HeaderBar(QWidget):
    """Application header bar with logo and title — Win11 style."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(52)
        self.setStyleSheet(f"""
            HeaderBar {{
                background-color: {Colors.BG_MICA};
                border-bottom: 1px solid {Colors.BORDER_DIVIDER};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(0)

        # Logo circle — Win11 rounded square icon style
        logo = QLabel("⚡")
        logo.setFixedSize(34, 34)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet(f"""
            background-color: {Colors.ACCENT};
            color: white;
            border-radius: 8px;
            font-size: 16px;
            font-weight: bold;
        """)
        layout.addWidget(logo)

        # App name
        name_label = QLabel("ToolHub")
        name_label.setStyleSheet(f"""
            color: {Colors.TEXT};
            font-size: 16px;
            font-weight: 600;
            margin-left: 10px;
            background: transparent;
        """)
        layout.addWidget(name_label)

        # Subtitle
        sub_label = QLabel("MEDIA TOOLS")
        sub_label.setStyleSheet(f"""
            color: {Colors.TEXT_TERTIARY};
            font-size: 11px;
            font-weight: 500;
            letter-spacing: 1px;
            margin-left: 8px;
            margin-top: 2px;
            background: transparent;
        """)
        layout.addWidget(sub_label)

        layout.addStretch()
