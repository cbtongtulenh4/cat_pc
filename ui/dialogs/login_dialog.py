"""
Login Dialog — Windows 11 Fluent Design sign-in screen.
Shown before the main application window.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QWidget, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QFont
from qfluentwidgets import (
    PrimaryPushButton, PasswordLineEdit, CheckBox,
    IndeterminateProgressRing, InfoBar, InfoBarPosition
)
from PyQt6.QtCore import QTimer
from ui.theme import Colors
from core.auth import AuthService


class _LoginWorker(QThread):
    """Background thread for API call — keeps UI responsive."""
    finished = pyqtSignal(dict)  # API response

    def __init__(self, token: str):
        super().__init__()
        self._token = token

    def run(self):
        result = AuthService.instance().login(self._token)
        self.finished.emit(result)


class LoginDialog(QDialog):
    """Modal login dialog — Win11 Fluent Design style."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: _LoginWorker | None = None

        self.setWindowTitle("ToolHub — Sign In")
        self.setFixedSize(420, 520)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setStyleSheet(f"background-color: {Colors.BG_MICA};")

        self._init_ui()
        self._center_on_screen()
        self._try_auto_login()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Central Card ──
        card = QWidget()
        card.setStyleSheet(f"""
            QWidget {{
                background-color: {Colors.BG_PANEL};
                border: 1px solid {Colors.BORDER_CARD};
                border-radius: 12px;
            }}
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(36, 40, 36, 32)
        card_layout.setSpacing(0)

        # ── Logo ──
        logo = QLabel("⚡")
        logo.setFixedSize(56, 56)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet(f"""
            background-color: {Colors.ACCENT};
            color: white;
            border-radius: 14px;
            font-size: 26px;
            font-weight: bold;
            border: none;
        """)
        card_layout.addWidget(logo, 0, Qt.AlignmentFlag.AlignCenter)

        card_layout.addSpacing(16)

        # ── Title ──
        title = QLabel("ToolHub")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"""
            color: {Colors.TEXT};
            font-size: 22px;
            font-weight: 700;
            background: transparent;
            border: none;
        """)
        card_layout.addWidget(title)

        card_layout.addSpacing(4)

        # ── Subtitle ──
        subtitle = QLabel("Video Editor Pro")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(f"""
            color: {Colors.TEXT_TERTIARY};
            font-size: 13px;
            font-weight: 400;
            background: transparent;
            border: none;
        """)
        card_layout.addWidget(subtitle)

        card_layout.addSpacing(32)

        # ── Token Input ──
        input_label = QLabel("Access Token")
        input_label.setStyleSheet(f"""
            color: {Colors.TEXT_SECONDARY};
            font-size: 12px;
            font-weight: 500;
            background: transparent;
            border: none;
            margin-bottom: 4px;
        """)
        card_layout.addWidget(input_label)

        card_layout.addSpacing(4)

        self._token_input = PasswordLineEdit()
        self._token_input.setPlaceholderText("Enter your access token...")
        self._token_input.setFixedHeight(40)
        self._token_input.setClearButtonEnabled(True)
        self._token_input.returnPressed.connect(self._on_login_clicked)
        card_layout.addWidget(self._token_input)

        card_layout.addSpacing(12)

        # ── Remember Me ──
        self._remember_check = CheckBox("Remember me")
        self._remember_check.setChecked(True)
        self._remember_check.setStyleSheet(f"""
            QCheckBox {{
                color: {Colors.TEXT_SECONDARY};
                font-size: 12px;
                background: transparent;
                border: none;
            }}
        """)
        card_layout.addWidget(self._remember_check)

        card_layout.addSpacing(20)

        # ── Login Button ──
        self._btn_login = PrimaryPushButton("🔑  Sign In")
        self._btn_login.setFixedHeight(42)
        self._btn_login.clicked.connect(self._on_login_clicked)
        card_layout.addWidget(self._btn_login)

        card_layout.addSpacing(12)

        # ── Loading Spinner (Inside Button) ──
        self._spinner = IndeterminateProgressRing(self._btn_login)
        self._spinner.setFixedSize(20, 20)
        
        # Center the spinner and text in the button
        btn_layout = QHBoxLayout(self._btn_login)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(10)
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        btn_layout.addStretch() # Left stretch
        btn_layout.addWidget(self._spinner)
        
        self._lbl_loading = QLabel("Đang xử lý...")
        self._lbl_loading.setStyleSheet("color: white; font-size: 13px; font-weight: 500; background: transparent; border: none;")
        self._lbl_loading.hide()
        btn_layout.addWidget(self._lbl_loading)
        btn_layout.addStretch() # Right stretch
        
        self._spinner.hide()

        card_layout.addStretch()

        # ── Version footer ──
        version = QLabel("v2.0.0")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version.setStyleSheet(f"""
            color: {Colors.TEXT_MUTED};
            font-size: 11px;
            background: transparent;
            border: none;
        """)
        card_layout.addWidget(version)

        # ── Add card to main layout with margins ──
        layout.addSpacing(16)
        wrapper = QHBoxLayout()
        wrapper.setContentsMargins(16, 0, 16, 16)
        wrapper.addWidget(card)
        layout.addLayout(wrapper, 1)

    # ── Auto Login (Remember Me) ──

    def _try_auto_login(self):
        """Try to auto-login with saved token."""
        auth = AuthService.instance()
        saved_token = auth.load_saved_token()
        if saved_token:
            self._token_input.setText(saved_token)
            self._remember_check.setChecked(True)
            # Removed auto-submit to allow user to change token if needed

    # ── Login Flow ──

    def _on_login_clicked(self):
        token = self._token_input.text().strip()
        if not token:
            self._show_error("Vui lòng nhập token")
            return

        # Disable UI during login
        self._set_loading(True)

        # Run login in background thread
        self._worker = _LoginWorker(token)
        self._worker.finished.connect(self._on_login_result)
        self._worker.start()

    def _on_login_result(self, result: dict):
        """Handle API response."""
        self._set_loading(False)

        if result.get("status"):
            # ── Success ──
            # Save token if "remember me" is checked
            auth = AuthService.instance()
            if self._remember_check.isChecked():
                auth.save_token(self._token_input.text().strip())
            else:
                auth.clear_saved_token()

            # Show success briefly then close
            name = result.get('user', 'admin')
            if not name:
                name = 'User'
            InfoBar.success(
                title="Đăng nhập thành công",
                content=f"Chào mừng, {name}!",
                orient=Qt.Orientation.Horizontal,
                isClosable=False,
                position=InfoBarPosition.TOP,
                duration=1500,
                parent=self,
            )
            QTimer.singleShot(1200, self.accept)

        else:
            # ── Failure ──
            error_msg = result.get("error", "Token không hợp lệ")
            if "Max retries exceeded" in error_msg or "google" in error_msg:
                error_msg = "Vui lòng thử lại sau 1 phút."
            self._show_error(error_msg)

            # Clear saved token on failure
            AuthService.instance().clear_saved_token()

    # ── UI Helpers ──

    def _set_loading(self, loading: bool):
        """Toggle loading state."""
        self._btn_login.setEnabled(not loading)
        self._token_input.setEnabled(not loading)
        self._remember_check.setEnabled(not loading)

        if loading:
            self._btn_login.setText("")  # Hide main text
            self._lbl_loading.show()
            self._spinner.show()
            self._spinner.start()
        else:
            self._spinner.stop()
            self._spinner.hide()
            self._lbl_loading.hide()
            self._btn_login.setText("🔑  Sign In")

    def _center_on_screen(self):
        """Center the dialog on the current screen."""
        frame_gm = self.frameGeometry()
        screen_center = self.screen().availableGeometry().center()
        frame_gm.moveCenter(screen_center)
        self.move(frame_gm.topLeft())

    def _show_error(self, message: str):
        """Show error notification."""
        InfoBar.error(
            title="Đăng nhập thất bại",
            content=message,
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=4000,
            parent=self,
        )
