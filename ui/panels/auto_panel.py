"""
Auto Panel — Grid of filter toggle cards.
Matches the 'AUTO TOOLS' tab — Windows 11 Fluent Design style.
Updated with Responsive FlowLayout.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from qfluentwidgets import (
    PrimaryPushButton, SmoothScrollArea, IconWidget, 
    Icon, FluentIcon as FIF, InfoBar, InfoBarPosition
)
from ui.theme import Colors
from ui.layouts import FlowLayout
from core.config import APP_ROOT


class _FilterCard(QPushButton):
    """
    Toggleable filter card — Win11 settings card style.
    Subtle elevation, rounded corners, clean hover.
    """

    def __init__(self, filter_id: str, fluent_icon: FIF, label: str, parent=None):
        super().__init__(parent)
        self.filter_id = filter_id
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(195, 90)
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 14, 10, 14)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Icon
        self.icon_widget = IconWidget(fluent_icon)
        self.icon_widget.setFixedSize(30, 30)
        layout.addWidget(self.icon_widget, 0, Qt.AlignmentFlag.AlignCenter)

        # Label
        self.text_label = QLabel(label.replace("\n", " "))
        self.text_label.setWordWrap(True)
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text_label.setStyleSheet(
            f"font-size: 11px; font-weight: 500; background: transparent; "
            f"color: {Colors.TEXT_SECONDARY};"
        )
        layout.addWidget(self.text_label, 0, Qt.AlignmentFlag.AlignCenter)

        self._update_style()
        self.toggled.connect(self._update_style)

    def _update_style(self):
        if self.isChecked():
            # Win11 selected card: subtle accent bg, accent border
            self.setStyleSheet(f"""
                _FilterCard {{
                    background-color: {Colors.ACCENT_BG};
                    border: 1px solid {Colors.ACCENT_BORDER};
                    border-radius: 8px;
                }}
            """)
            self.text_label.setStyleSheet(
                f"font-size: 11px; font-weight: 600; background: transparent; "
                f"color: {Colors.ACCENT_LIGHT};"
            )
        else:
            # Win11 idle card: elevated surface, subtle border
            self.setStyleSheet(f"""
                _FilterCard {{
                    background-color: {Colors.BG_CARD};
                    border: 1px solid {Colors.BORDER_CARD};
                    border-radius: 8px;
                }}
                _FilterCard:hover {{
                    background-color: {Colors.BG_CARD_HOVER};
                    border-color: {Colors.BORDER_LIGHT};
                }}
            """)
            self.text_label.setStyleSheet(
                f"font-size: 11px; font-weight: 500; background: transparent; "
                f"color: {Colors.TEXT_SECONDARY};"
            )


class AutoPanel(QWidget):
    """Auto filters panel using FlowLayout — Win11 style."""

    settings_changed = pyqtSignal(dict)

    # Filter definitions: (id, FluentIcon, label)
    FILTERS = [
        ("brightness",    str(APP_ROOT / "assets/icons/brightness.svg"), "Tăng độ sáng nhẹ"),
        ("contrast",      str(APP_ROOT / "assets/icons/contrast.svg"),   "Tăng độ tương phản"),
        ("sharpen",       str(APP_ROOT / "assets/icons/sharpen.svg"),    "Làm sắc nét"),
        ("blur_light",    str(APP_ROOT / "assets/icons/blur.svg"),       "Làm mờ nhẹ"),
        ("bw",            str(APP_ROOT / "assets/icons/bw.svg"),         "Đen trắng"),
        ("vignette",      str(APP_ROOT / "assets/icons/vignette.svg"),   "Vignette nhẹ"),
        ("saturation",    str(APP_ROOT / "assets/icons/saturation.svg"), "Tăng độ bão hòa"),
        ("color_balance", str(APP_ROOT / "assets/icons/color_balance.svg"), "Cân bằng màu sắc"),
        ("skin_smooth",   str(APP_ROOT / "assets/icons/skin_smooth.svg"), "Làm mịn da"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {Colors.BG_PANEL};")

        # Debounce timer — coalesce rapid toggle changes
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(120)  # 120 ms
        self._debounce.timeout.connect(self._do_emit)

        # Scroll area
        scroll = SmoothScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(14, 16, 14, 14)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Title — Win11 section header
        title = QLabel("Auto Tools")
        title.setStyleSheet(f"""
            color: {Colors.TEXT};
            font-size: 14px;
            font-weight: 600;
            background: transparent;
        """)
        layout.addWidget(title)

        # Filter FlowLayout Container
        self.grid_container = QWidget()
        self.flow_layout = FlowLayout(self.grid_container, spacing=10)
        self.flow_layout.setContentsMargins(0, 8, 0, 8)

        self._cards: dict[str, _FilterCard] = {}
        for fid, icon, label in self.FILTERS:
            card = _FilterCard(fid, icon, label)
            card.toggled.connect(lambda _, c=card: self._on_toggle(c))
            self._cards[fid] = card
            self.flow_layout.addWidget(card)

        layout.addWidget(self.grid_container)
        
        scroll.setWidget(container)

        # Main overall layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(scroll)

        # Sticky Footer Section — Win11 style
        footer = QWidget()
        footer.setObjectName("footer")
        footer.setStyleSheet(f"""
            QWidget#footer {{ 
                background-color: {Colors.BG_PANEL}; 
                border-top: 1px solid {Colors.BORDER_DIVIDER}; 
            }}
        """)
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(14, 12, 14, 12)

        self._btn_apply = PrimaryPushButton("✨  APPLY FILTERS")
        self._btn_apply.setFixedHeight(44)
        self._btn_apply.clicked.connect(self._on_apply_clicked)
        footer_layout.addWidget(self._btn_apply)

        main_layout.addWidget(footer)

    def _on_toggle(self, card: _FilterCard):
        self._emit_settings()

    def _on_apply_clicked(self):
        """Handle big button click with notification."""
        InfoBar.success(
            title="Thành công",
            content="Đã áp dụng bộ lọc tự động.",
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self.window()
        )
        self._emit_settings()

    def _emit_settings(self):
        """Schedule a debounced emission of settings."""
        self._debounce.start()

    def _do_emit(self):
        """Actually emit settings (called after debounce timer fires)."""
        self.settings_changed.emit(self.get_settings())

    def get_settings(self) -> dict:
        active = [fid for fid, card in self._cards.items() if card.isChecked()]
        return {"auto_filters": active}

    def load_settings(self, settings: dict):
        active = settings.get("auto_filters", [])
        for fid, card in self._cards.items():
            card.blockSignals(True)
            card.setChecked(fid in active)
            card.blockSignals(False)
