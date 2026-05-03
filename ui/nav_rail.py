"""
Navigation Rail — Vertical icon sidebar (72px width).
Windows 11 Fluent Design style with pill-shaped active indicator.
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QButtonGroup, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from qfluentwidgets import FluentIcon as FIF, IconWidget
from ui.theme import Colors


class _NavButton(QPushButton):
    """
    Vertical nav button with Icon on top and Text on bottom.
    Win11 style: rounded hover, pill indicator on left.
    """

    def __init__(self, fluent_icon: FIF, label: str, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(72, 68) 
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Layout for Icon + Text
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 8)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Icon
        self.icon_widget = IconWidget(fluent_icon)
        self.icon_widget.setFixedSize(24, 24)
        layout.addWidget(self.icon_widget, 0, Qt.AlignmentFlag.AlignCenter)

        # Label
        self.text_label = QLabel(label)
        self.text_label.setStyleSheet(
            f"font-size: 11px; font-weight: 500; background: transparent;"
        )
        layout.addWidget(self.text_label, 0, Qt.AlignmentFlag.AlignCenter)

        self._update_style()
        self.toggled.connect(self._update_style)

    def _update_style(self):
        if self.isChecked():
            # Active state — Win11: subtle bg, pill indicator, accent text
            self.setStyleSheet(f"""
                _NavButton {{
                    background-color: rgba(255, 255, 255, 0.06);
                    border: none;
                    border-left: 3px solid {Colors.ACCENT};
                    border-radius: 0px;
                }}
            """)
            self.text_label.setStyleSheet(
                f"color: {Colors.TEXT}; font-size: 11px; "
                f"font-weight: 600; background: transparent;"
            )
        else:
            # Idle state — Win11: transparent, subtle hover
            self.setStyleSheet(f"""
                _NavButton {{
                    background-color: transparent;
                    border: none;
                    border-left: 3px solid transparent;
                    border-radius: 0px;
                }}
                _NavButton:hover {{
                    background-color: rgba(255, 255, 255, 0.04);
                }}
            """)
            self.text_label.setStyleSheet(
                f"color: {Colors.TEXT_TERTIARY}; font-size: 11px; "
                f"font-weight: 500; background: transparent;"
            )


class NavRail(QWidget):
    """Vertical navigation rail — 72px wide, Win11 style."""

    tab_changed = pyqtSignal(int)  # tab index

    # Tab definitions: (FluentIcon, Label)
    TABS = [
        (FIF.BRUSH,    "Auto"),      # Like auto_fix_high
        (FIF.FILTER,   "Custom"),     # Like tune (sliders)
        (FIF.MOVIE,    "Media"),      # Like perm_media
        (FIF.FONT,     "Text"),       # Like title
        (FIF.MUSIC,    "Audio"),      # Like audiotrack
        (FIF.TILES,    "Templates"),  # Like dashboard_customize
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(72)
        self.setStyleSheet(f"""
            NavRail {{
                background-color: {Colors.BG_MICA};
                border-right: 1px solid {Colors.BORDER_DIVIDER};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 10)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        from core.auth import AuthService
        auth = AuthService.instance()
        is_admin = (auth.user == "admin")

        self._btn_group = QButtonGroup(self)
        self._btn_group.setExclusive(True)

        for i, (icon, label) in enumerate(self.TABS):
            btn = _NavButton(icon, label)
            self._btn_group.addButton(btn, i)
            layout.addWidget(btn)
            
            # ── Permission Logic ──
            if not is_admin and label in ["Auto", "Media", "Text", "Audio", "Templates"]:
                btn.hide()
                
            # Default selection
            if is_admin:
                if i == 0:  # Auto
                    btn.setChecked(True)
            else:
                if label == "Custom":
                    btn.setChecked(True)

        layout.addStretch()

        self._btn_group.idClicked.connect(self.tab_changed.emit)

    def set_tab(self, index: int):
        """Programmatically select a tab."""
        btn = self._btn_group.button(index)
        if btn:
            btn.setChecked(True)
            # Force style update because property change might not trigger if signals blocked
            btn._update_style()
            self.tab_changed.emit(index)
