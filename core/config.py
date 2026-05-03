import os
import sys
from pathlib import Path

def get_internal_root() -> Path:
    """Get the internal resource directory (temp folder in onefile mode)."""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(os.path.dirname(os.path.abspath(__file__))).parent

def get_app_root() -> Path:
    """Get the directory where the .exe or main.py is located."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(os.path.dirname(os.path.abspath(__file__))).parent


def get_bin_dir() -> Path:
    """
    Locate the bin directory containing ffmpeg/ffprobe.
    Search order:
      1. Internal bundled folder (bins)
      2. External app folder (ffmpeg)
    """
    # 1. Check internal bundle first (for 'bins')
    internal_root = get_internal_root()
    p_internal = internal_root / "bins"
    if p_internal.exists() and (p_internal / "ffmpeg.exe").exists():
        return p_internal

    # 2. Check external app root (for 'ffmpeg')
    app_root = get_app_root()
    p_external = app_root / "ffmpeg"
    if p_external.exists() and (p_external / "ffmpeg.exe").exists():
        return p_external

    # 3. Fallback to system PATH
    return Path(".")


def get_templates_dir() -> Path:
    """Get the templates directory (External)."""
    return get_app_root() / "templates"


# Resolved paths (import these directly)
INTERNAL_ROOT = get_internal_root()
APP_ROOT = get_app_root()
BIN_DIR = get_bin_dir()
FFMPEG_PATH = str(BIN_DIR / "ffmpeg.exe")
FFPROBE_PATH = str(BIN_DIR / "ffprobe.exe")
TEMPLATES_DIR = get_templates_dir()

# Ensure external templates dir exists
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
