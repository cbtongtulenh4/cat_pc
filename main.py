"""
Video Editor Pro — Desktop V2
Entry point with Windows 11 Fluent Design dark theme (qfluentwidgets).
"""
import sys
import os
import logging
from PyQt6.QtWidgets import QApplication, QDialog
from PyQt6.QtGui import QFont

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("main")


def main():
    # Ensure module imports work
    app_dir = os.path.dirname(os.path.abspath(__file__))
    if app_dir not in sys.path:
        sys.path.insert(0, app_dir)

    # Setup MPV PATH before any imports that might use it
    bins_path = os.path.join(app_dir, "bins")
    if os.path.exists(bins_path):
        os.environ["PATH"] = bins_path + os.pathsep + os.environ["PATH"]
    # Create application FIRST before any other imports
    app = QApplication(sys.argv)
    app.setApplicationName("ToolHub - Video Editor")
    app.setApplicationVersion("2.0.0")

    from qfluentwidgets import setTheme, Theme, setThemeColor
    from ui.theme import WIN11_GLOBAL_STYLE
    from ui.dialogs.login_dialog import LoginDialog

    # Set Fluent dark theme (Win11)
    setTheme(Theme.DARK)
    setThemeColor('#7c3aed')  # purple accent

    # Win11 global stylesheet for consistent appearance
    app.setStyleSheet(WIN11_GLOBAL_STYLE)

    # Default font — Segoe UI Variable (Win11) with fallback
    font = QFont("Segoe UI Variable", 10)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(font)

    # ═══ STEP 1: Login ═══
    login_dialog = LoginDialog()
    result = login_dialog.exec()

    if result != QDialog.DialogCode.Accepted:
        logger.info("Login cancelled — exiting")
        sys.exit(0)

    # ═══ STEP 2: Main Window (only after successful login) ═══
    from ui.main_window import MainWindow

    window = MainWindow()
    window.show()

    logger.info("ToolHub Video Editor started (Windows 11 Fluent Design)")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
