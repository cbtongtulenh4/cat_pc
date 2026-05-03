"""
Qt Signal/Slot definitions for batch processing progress reporting.
These signals bridge the batch worker thread with the PyQt6 UI thread.
"""
from PyQt6.QtCore import QObject, pyqtSignal


class BatchSignals(QObject):
    """Signals emitted by the batch processor to update the UI."""

    # Scanning for video files
    scanning = pyqtSignal()

    # Processing started with total file count
    started = pyqtSignal(int)  # total_files

    # Individual file progress
    file_progress = pyqtSignal(str, int)  # path, percent (0-100)

    # File completed/failed/skipped
    file_done = pyqtSignal(str, str, int, str)  # path, status ("done"/"error"/"skipped"), completed_count, message

    # All processing completed
    completed = pyqtSignal(int, int, int)  # total, completed, skipped

    # Processing cancelled
    cancelled = pyqtSignal(int)  # total

    # Error occurred
    error = pyqtSignal(str)  # error message

    # Log message for status bar
    log = pyqtSignal(str)  # log message
