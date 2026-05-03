"""
Template Panel — Save / Load / Delete edit templates.
Windows 11 Fluent Design style.
"""
import os
import json
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem
)
from PyQt6.QtCore import Qt, pyqtSignal
from qfluentwidgets import (
    PrimaryPushButton, PushButton, LineEdit, SmoothScrollArea,
    MessageBox
)
from core.config import TEMPLATES_DIR
from ui.theme import Colors


class TemplatePanel(QWidget):
    """Panel for managing edit templates — Win11 style."""

    template_loaded = pyqtSignal(dict)  # emits settings dict

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_settings: dict = {}
        self.setStyleSheet(f"background-color: {Colors.BG_PANEL};")
        self._init_ui()
        self._refresh_list()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 16, 14, 14)
        layout.setSpacing(10)

        # Title — Win11 section header
        title = QLabel("Templates")
        title.setStyleSheet(f"""
            color: {Colors.TEXT};
            font-size: 14px;
            font-weight: 600;
            background: transparent;
        """)
        layout.addWidget(title)

        # Save section
        layout.addWidget(self._field_label("SAVE CURRENT SETTINGS"))
        save_row = QHBoxLayout()
        self._name_input = LineEdit()
        self._name_input.setPlaceholderText("Template name...")
        self._name_input.setFixedHeight(36)
        save_row.addWidget(self._name_input, 1)

        btn_save = PrimaryPushButton("💾 Save")
        btn_save.setFixedHeight(36)
        btn_save.setFixedWidth(100)
        btn_save.clicked.connect(self._save_template)
        save_row.addWidget(btn_save)
        layout.addLayout(save_row)

        # Separator — Win11 divider
        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {Colors.BORDER_DIVIDER};")
        layout.addWidget(sep)

        # Template list — Win11 ListView style
        layout.addWidget(self._field_label("SAVED TEMPLATES"))
        self._list = QListWidget()
        self._list.setStyleSheet(f"""
            QListWidget {{
                background-color: {Colors.BG_CARD};
                border: 1px solid {Colors.BORDER_CARD};
                border-radius: 8px;
                outline: none;
            }}
            QListWidget::item {{
                padding: 12px 14px;
                border-bottom: 1px solid {Colors.BORDER_DIVIDER};
                color: {Colors.TEXT};
            }}
            QListWidget::item:selected {{
                background-color: {Colors.ACCENT_BG};
                color: {Colors.ACCENT_LIGHT};
            }}
            QListWidget::item:hover {{
                background-color: {Colors.BG_CARD_HOVER};
            }}
        """)
        layout.addWidget(self._list, 1)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_load = PrimaryPushButton("📂 Load")
        btn_load.setFixedHeight(36)
        btn_load.clicked.connect(self._load_selected)
        btn_row.addWidget(btn_load)

        btn_delete = PushButton("🗑 Delete")
        btn_delete.setFixedHeight(36)
        btn_delete.setStyleSheet(f"""
            QPushButton {{
                color: {Colors.ERROR};
                border: 1px solid rgba(255, 107, 107, 0.3);
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background: rgba(255, 107, 107, 0.1);
            }}
        """)
        btn_delete.clicked.connect(self._delete_selected)
        btn_row.addWidget(btn_delete)

        layout.addLayout(btn_row)

    def set_current_settings(self, settings: dict):
        """Update the settings that will be saved when user clicks Save."""
        self._current_settings = settings

    def _refresh_list(self):
        self._list.clear()
        if not TEMPLATES_DIR.exists():
            return
        for f in sorted(TEMPLATES_DIR.glob("*.json")):
            try:
                with open(f, 'r', encoding='utf-8') as fp:
                    data = json.load(fp)
                name = data.get("name", f.stem)
                desc = data.get("description", "")
                item = QListWidgetItem(f"{name}\n  {desc}")
                item.setData(Qt.ItemDataRole.UserRole, str(f))
                self._list.addItem(item)
            except Exception:
                continue

    def _save_template(self):
        name = self._name_input.text().strip()
        if not name:
            return
        safe = "".join(c for c in name if c.isalnum() or c in " _-").strip() or "template"
        filepath = TEMPLATES_DIR / f"{safe}.json"
        data = {
            "name": name,
            "description": f"Created {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "created_at": datetime.now().isoformat(),
            "settings": self._current_settings,
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        self._name_input.clear()
        self._refresh_list()

    def _load_selected(self):
        item = self._list.currentItem()
        if not item:
            return
        filepath = item.data(Qt.ItemDataRole.UserRole)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.template_loaded.emit(data.get("settings", {}))
        except Exception:
            pass

    def _delete_selected(self):
        item = self._list.currentItem()
        if not item:
            return
        filepath = item.data(Qt.ItemDataRole.UserRole)
        try:
            os.remove(filepath)
            self._refresh_list()
        except Exception:
            pass

    @staticmethod
    def _field_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color: {Colors.TEXT_TERTIARY}; font-size: 11px; font-weight: 500; "
            f"letter-spacing: 0.5px; background: transparent;"
        )
        return lbl
