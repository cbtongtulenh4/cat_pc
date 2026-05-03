"""
Batch Progress Dialog — Windows 11 Fluent Design styled progress dialog.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QWidget
)
from PyQt6.QtCore import Qt
from qfluentwidgets import ProgressBar, PrimaryPushButton, PushButton, SubtitleLabel
from ui.theme import Colors
import os


class BatchProgressDialog(QDialog):
    """Modal dialog showing batch video processing progress — Win11 style."""

    def __init__(self, total_files: int, parent=None):
        super().__init__(parent)
        self._total = total_files
        self._completed = 0
        self._success = 0
        self._errors = 0
        self._skipped = 0
        self.setWindowTitle("Processing Videos...")
        self.setMinimumSize(600, 450)
        self.setStyleSheet(f"background-color: {Colors.BG_PANEL};")
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.WindowTitleHint | Qt.WindowType.CustomizeWindowHint
        )
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        # Header — Win11 style
        header = SubtitleLabel("⚡ Batch Processing")
        header.setStyleSheet(f"color: {Colors.TEXT}; font-weight: 600;")
        layout.addWidget(header)

        # Stats row
        stats = QWidget()
        stats.setStyleSheet("background: transparent;")
        s_layout = QHBoxLayout(stats)
        s_layout.setContentsMargins(0, 0, 0, 0)

        self._lbl_progress = QLabel(f"0 / {self._total}")
        self._lbl_progress.setStyleSheet(f"""
            font-size: 28px; font-weight: 600;
            color: {Colors.TEXT}; background: transparent;
        """)
        s_layout.addWidget(self._lbl_progress)
        s_layout.addStretch()

        self._lbl_success = QLabel("✅ 0")
        self._lbl_success.setStyleSheet(f"color: {Colors.SUCCESS}; font-weight: 500; background: transparent;")
        s_layout.addWidget(self._lbl_success)

        self._lbl_error = QLabel("❌ 0")
        self._lbl_error.setStyleSheet(f"color: {Colors.ERROR}; font-weight: 500; background: transparent;")
        s_layout.addWidget(self._lbl_error)

        self._lbl_skipped = QLabel("⏭ 0")
        self._lbl_skipped.setStyleSheet(f"color: {Colors.WARNING}; font-weight: 500; background: transparent;")
        s_layout.addWidget(self._lbl_skipped)

        layout.addWidget(stats)

        # Progress bar — Win11 thin style
        self._progress = ProgressBar()
        self._progress.setRange(0, self._total)
        self._progress.setValue(0)
        self._progress.setFixedHeight(4)
        layout.addWidget(self._progress)

        # Current file
        self._current_file = QLabel("Scanning folder...")
        self._current_file.setStyleSheet(f"""
            color: {Colors.TEXT_TERTIARY};
            font-size: 13px;
            background: transparent;
        """)
        self._current_file.setWordWrap(True)
        layout.addWidget(self._current_file)

        # Log — Win11 card style
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumHeight(120)
        self._log.setStyleSheet(f"""
            QTextEdit {{
                background: {Colors.BG_MICA};
                border: 1px solid {Colors.BORDER_CARD};
                border-radius: 8px;
                color: {Colors.TEXT_TERTIARY};
                font-size: 12px;
                font-family: Consolas;
                padding: 8px;
            }}
        """)
        layout.addWidget(self._log)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._btn_cancel = PushButton("⬛ Cancel")
        self._btn_cancel.setFixedWidth(140)
        self._btn_cancel.setStyleSheet(f"""
            QPushButton {{
                color: {Colors.ERROR};
                border: 1px solid rgba(255, 107, 107, 0.3);
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background: rgba(255, 107, 107, 0.1);
            }}
        """)
        btn_row.addWidget(self._btn_cancel)

        self._btn_close = PrimaryPushButton("Close")
        self._btn_close.setFixedWidth(100)
        self._btn_close.setVisible(False)
        self._btn_close.clicked.connect(self.accept)
        btn_row.addWidget(self._btn_close)

        layout.addLayout(btn_row)

    @property
    def cancel_button(self):
        return self._btn_cancel

    def on_scanning(self):
        self._current_file.setText("🔍 Scanning folder for videos...")

    def on_started(self, total: int):
        self._total = total
        self._progress.setRange(0, total)
        self._lbl_progress.setText(f"0 / {total}")

    def on_file_progress(self, path: str, percent: int):
        name = os.path.basename(path)
        self._current_file.setText(f"⏳ {name} — {percent}%")

    def on_file_done(self, path: str, status: str, completed: int, message: str = ""):
        name = os.path.basename(path)
        self._completed = completed
        self._progress.setValue(completed)
        self._lbl_progress.setText(f"{completed} / {self._total}")

        suffix = f" — {message}" if message else ""
        if status == "success" or status == "done":
            self._success += 1
            self._lbl_success.setText(f"✅ {self._success}")
            self._log.append(f"✅ {name}{suffix}")
        elif status == "error":
            self._errors += 1
            self._lbl_error.setText(f"❌ {self._errors}")
            self._log.append(f"❌ {name}{suffix}")
        elif status == "skipped" or status == "skip":
            self._skipped += 1
            self._lbl_skipped.setText(f"⏭ {self._skipped}")
            self._log.append(f"⏭ {name}{suffix}")

    def on_completed(self, total: int, completed: int, skipped: int):
        self._progress.setValue(total)
        self._lbl_progress.setText(f"{total} / {total}")
        self._current_file.setText("🎉 Complete!")
        self._current_file.setStyleSheet(f"""
            color: {Colors.SUCCESS};
            font-size: 12px;
            font-weight: 600;
            background: transparent;
        """)
        self._btn_cancel.setVisible(False)
        self._btn_close.setVisible(True)

    def on_cancelled(self, total: int):
        self._current_file.setText("⚠️ Cancelled by user")
        self._current_file.setStyleSheet(f"""
            color: {Colors.WARNING};
            font-size: 12px;
            font-weight: 600;
            background: transparent;
        """)
        self._btn_cancel.setVisible(False)
        self._btn_close.setVisible(True)

    def on_error(self, message: str):
        self._current_file.setText(f"❌ Error: {message}")
        self._current_file.setStyleSheet(f"""
            color: {Colors.ERROR};
            font-size: 12px;
            background: transparent;
        """)
        self._btn_cancel.setVisible(False)
        self._btn_close.setVisible(True)

    def on_log(self, message: str):
        self._log.append(f"ℹ️ {message}")
