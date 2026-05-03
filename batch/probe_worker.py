"""
Worker for background video probing.
"""
from PyQt6.QtCore import QThread, pyqtSignal
from core.video_info import get_video_info

class ProbeWorker(QThread):
    """
    Background worker to get video info (duration, etc.) using ffprobe.
    """
    info_ready = pyqtSignal(str, dict)  # path, info_dict

    def __init__(self, paths: list[str], parent=None):
        super().__init__(parent)
        self.paths = paths
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        for path in self.paths:
            if self._is_cancelled:
                break
            info = get_video_info(path)
            self.info_ready.emit(path, info)
