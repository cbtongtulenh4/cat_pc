"""
Render Toolbar — Full-width horizontal bar with render configuration.
Windows 11 Fluent Design style.
"""
import os
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from qfluentwidgets import (
    LineEdit, ComboBox, SpinBox, CheckBox,
    PrimaryPushButton, PushButton, CaptionLabel, ToolButton,
    FluentIcon as FIF, SwitchButton
)
from ui.theme import Colors
from core.config import APP_ROOT


class RenderToolbar(QWidget):
    """Horizontal render configuration bar — spans full window width. Win11 style."""

    render_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    check_clicked = pyqtSignal()  # New signal
    clear_clicked = pyqtSignal()
    folder_changed = pyqtSignal(str)
    edit_mode_changed = pyqtSignal(bool)  # True = sync, False = individual

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(52)
        self.setStyleSheet(f"""
            RenderToolbar {{
                background-color: {Colors.BG_PANEL};
                border-top: 1px solid {Colors.BORDER_DIVIDER};
                border-bottom: 1px solid {Colors.BORDER_DIVIDER};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(8)

        # Folder icon
        folder_icon = ToolButton(FIF.FOLDER.icon())
        folder_icon.setFixedSize(32, 32)
        folder_icon.setStyleSheet("border: none; background: transparent;")
        layout.addWidget(folder_icon)

        # Path input
        self._save_path = LineEdit()
        self._save_path.setPlaceholderText("Chọn thư mục lưu trữ...")
        self._save_path.setReadOnly(False)
        self._save_path.setFixedWidth(300)
        self._save_path.setFixedHeight(32)
        
        # Set default path: video_output in APP_ROOT
        default_out = str(APP_ROOT / "video_output")
        if not os.path.exists(default_out):
            try: os.makedirs(default_out)
            except: pass
        self._save_path.setText(default_out)
        
        layout.addWidget(self._save_path)

        # Browse button
        btn_browse = ToolButton()
        btn_browse.setText("...")
        btn_browse.setFixedSize(32, 32)
        btn_browse.setToolTip("Chọn thư mục lưu trữ")
        btn_browse.clicked.connect(self._choose_save_folder)
        layout.addWidget(btn_browse)

        # Open folder button
        btn_open = PushButton(FIF.FOLDER_ADD.icon(), "Open")
        btn_open.setFixedHeight(32)
        btn_open.setToolTip("Mở thư mục lưu trữ")
        btn_open.clicked.connect(self._open_save_folder)
        layout.addWidget(btn_open)

        # Separator
        layout.addWidget(self._sep())

        # Format combo
        self._format_combo = ComboBox()
        self._format_combo.addItems(["MP4", "MKV", "AVI", "WEBM"])
        self._format_combo.setFixedWidth(100)
        self._format_combo.setFixedHeight(32)
        layout.addWidget(self._format_combo)

        # Resolution combo
        self._res_combo = ComboBox()
        self._res_combo.addItems(["Original", "1080p", "720p", "480p"])
        self._res_combo.setFixedWidth(110)
        self._res_combo.setFixedHeight(32)
        layout.addWidget(self._res_combo)

        # File count label
        self._file_count = CaptionLabel("0 files")
        self._file_count.setStyleSheet(f"""
            color: {Colors.TEXT_TERTIARY};
            font-weight: 500;
            font-size: 12px;
            background: transparent;
        """)
        layout.addWidget(self._file_count)

        layout.addWidget(self._sep())

        # Workers
        workers_label = CaptionLabel("Workers:")
        workers_label.setStyleSheet(f"""
            color: {Colors.TEXT_SECONDARY};
            font-size: 12px;
            background: transparent;
        """)
        layout.addWidget(workers_label)

        self._workers_spin = SpinBox()
        self._workers_spin.setRange(1, 1)
        self._workers_spin.setValue(1)
        self._workers_spin.setReadOnly(True)
        # Hide up/down buttons
        self._workers_spin.setButtonSymbols(SpinBox.ButtonSymbols.NoButtons)
        self._workers_spin.setFixedWidth(40)
        self._workers_spin.setFixedHeight(32)
        layout.addWidget(self._workers_spin)

        layout.addWidget(self._sep())

        # GPU checkbox
        self._gpu_check = CheckBox("Bật GPU")
        self._gpu_check.setChecked(False)
        layout.addWidget(self._gpu_check)

        # Delete original checkbox
        self._delete_check = CheckBox("Xóa video gốc")
        self._delete_check.setChecked(False)
        layout.addWidget(self._delete_check)

        layout.addWidget(self._sep())

        # Edit Mode Toggle: Sync / Individual
        self._edit_mode_label = CaptionLabel("")
        self._edit_mode_label.setStyleSheet(f"""
            color: {Colors.TEXT_SECONDARY};
            font-size: 11px;
            font-weight: 600;
            background: transparent;
        """)
        layout.addWidget(self._edit_mode_label)

        self._edit_mode_switch = SwitchButton()
        self._edit_mode_switch.setOnText("🔗 ĐỒNG BỘ")
        self._edit_mode_switch.setOffText("👤 RIÊNG LẺ")
        self._edit_mode_switch.setChecked(True)  # Default: sync mode
        self._edit_mode_switch.checkedChanged.connect(self._on_edit_mode_toggled)
        layout.addWidget(self._edit_mode_switch)

        layout.addStretch()
        # Clear button
        self._btn_clear = PushButton(FIF.DELETE.icon(), "Clear All")
        self._btn_clear.setFixedHeight(32)
        self._btn_clear.setToolTip("Xóa toàn bộ danh sách file")
        self._btn_clear.setEnabled(False)
        self._btn_clear.clicked.connect(self.clear_clicked.emit)
        layout.addWidget(self._btn_clear)

        # Check button
        self._btn_check = PushButton(FIF.ACCEPT.icon(), "Check Config")
        self._btn_check.setFixedHeight(34)
        self._btn_check.setFixedWidth(130)
        self._btn_check.setEnabled(False)
        self._btn_check.setToolTip("Kiểm tra thông số Crop/Trim/Logo trước khi Render")
        self._btn_check.clicked.connect(self.check_clicked.emit)
        layout.addWidget(self._btn_check)

        # Start button (primary)
        self._btn_apply = PrimaryPushButton(FIF.PLAY.icon(), "Start")
        self._btn_apply.setFixedHeight(34)
        self._btn_apply.setFixedWidth(160)
        self._btn_apply.setEnabled(False)
        self._btn_apply.clicked.connect(self.render_clicked.emit)
        layout.addWidget(self._btn_apply)

        # Stop button — Win11 danger/subtle style
        self._btn_stop = PushButton("Stop")
        self._btn_stop.setFixedHeight(34)
        self._btn_stop.setFixedWidth(70)
        self._btn_stop.setStyleSheet(f"""
            QPushButton {{
                color: {Colors.ERROR};
                border: 1px solid rgba(255, 107, 107, 0.3);
                border-radius: 6px;
                background: transparent;
            }}
            QPushButton:hover {{
                background: rgba(255, 107, 107, 0.1);
            }}
        """)
        self._btn_stop.clicked.connect(self.stop_clicked.emit)
        layout.addWidget(self._btn_stop)

    def _sep(self) -> QWidget:
        sep = QWidget()
        sep.setFixedSize(1, 22)
        sep.setStyleSheet(f"background-color: {Colors.BORDER};")
        return sep

    def _choose_save_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục lưu trữ")
        if folder:
            self._save_path.setText(folder)
            self.folder_changed.emit(folder)

    def _open_save_folder(self):
        """Open the selected folder in Windows Explorer."""
        path = self._save_path.text()
        if os.path.exists(path):
            os.startfile(path)

    # ── Public API ──

    @property
    def save_path(self) -> str:
        return self._save_path.text()

    @property
    def folder_path(self) -> str:
        """Alias for compatibility with MainWindow."""
        return self._save_path.text()

    @property
    def output_format(self) -> str:
        return self._format_combo.currentText().lower()

    @property
    def output_height(self):
        res = self._res_combo.currentText()
        mapping = {"1080p": 1080, "720p": 720, "480p": 480}
        return mapping.get(res, None)

    @property
    def workers(self) -> int:
        return self._workers_spin.value()

    @property
    def use_gpu(self) -> bool:
        return self._gpu_check.isChecked()

    @property
    def delete_original(self) -> bool:
        return self._delete_check.isChecked()

    def set_file_count(self, total: int, selected: int = 0):
        self._btn_clear.setEnabled(total > 0)
        if selected > 0:
            self._file_count.setText(f"{total} files • {selected} selected")
            self._btn_apply.setText(f"Start ({selected})")
            self._btn_apply.setEnabled(True)
            self._btn_check.setEnabled(True) # Sync with apply button
        else:
            self._file_count.setText(f"{total} files")
            self._btn_apply.setText(f"Start")
            self._btn_apply.setEnabled(False)
            self._btn_check.setEnabled(False)
            self._btn_check.setEnabled(False)

    def set_selected_count(self, selected: int):
        """Update enable state for action buttons."""
        self._btn_check.setEnabled(selected > 0)
        self._btn_apply.setEnabled(selected > 0)

    def set_progress(self, completed: int, total: int):
        """Update button text during processing."""
        if total > 0:
            self._btn_apply.setText(f"Processing ({completed}/{total})")
            self._btn_apply.setIcon(FIF.SYNC.icon())

    def reset_processing(self, total: int, selected: int = 0):
        """Reset button to idle state."""
        self._btn_apply.setIcon(FIF.PLAY.icon())
        self.set_file_count(total, selected)

    def set_folder(self, path: str):
        self._save_path.setText(path)

    @property
    def is_sync_mode(self) -> bool:
        return self._edit_mode_switch.isChecked()

    def _on_edit_mode_toggled(self, checked: bool):
        self.edit_mode_changed.emit(checked)
