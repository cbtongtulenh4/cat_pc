"""
Video information utilities using ffprobe.
Migrated from demo_server/video_editor.py — get_video_duration, get_video_height.
"""
import os
import subprocess
import logging

from core.config import FFPROBE_PATH

logger = logging.getLogger("video_info")

_CREATION_FLAGS = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0


def get_video_duration(path: str, ffprobe_path: str = None) -> float:
    """Get duration of a video file in seconds."""
    ffprobe = ffprobe_path or FFPROBE_PATH
    try:
        cmd = [
            ffprobe, "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", path
        ]
        result = subprocess.run(
            cmd, capture_output=True, encoding='utf-8', check=True,
            creationflags=_CREATION_FLAGS
        )
        return float(result.stdout.strip())
    except Exception as e:
        logger.error(f"Error getting duration for {path}: {e}")
        return 0


def get_video_height(path: str, ffprobe_path: str = None) -> int:
    """Get the video height in pixels using ffprobe."""
    ffprobe = ffprobe_path or FFPROBE_PATH
    try:
        cmd = [
            ffprobe, "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=height",
            "-of", "default=noprint_wrappers=1:nokey=1", path
        ]
        result = subprocess.run(
            cmd, capture_output=True, encoding='utf-8', check=True,
            creationflags=_CREATION_FLAGS
        )
        return int(result.stdout.strip())
    except Exception as e:
        logger.error(f"Error getting video height for {path}: {e}")
        return 0


def get_video_width(path: str, ffprobe_path: str = None) -> int:
    """Get the video width in pixels using ffprobe."""
    ffprobe = ffprobe_path or FFPROBE_PATH
    try:
        cmd = [
            ffprobe, "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width",
            "-of", "default=noprint_wrappers=1:nokey=1", path
        ]
        result = subprocess.run(
            cmd, capture_output=True, encoding='utf-8', check=True,
            creationflags=_CREATION_FLAGS
        )
        return int(result.stdout.strip())
    except Exception as e:
        logger.error(f"Error getting video width for {path}: {e}")
        return 0


def get_video_info(path: str, ffprobe_path: str = None) -> dict:
    """Get comprehensive video info: duration, width, height, fps, codec."""
    ffprobe = ffprobe_path or FFPROBE_PATH
    info = {
        "path": path,
        "duration": 0,
        "width": 0,
        "height": 0,
        "fps": 0,
        "codec": "",
    }
    try:
        cmd = [
            ffprobe, "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,r_frame_rate,codec_name",
            "-show_entries", "format=duration",
            "-of", "json", path
        ]
        result = subprocess.run(
            cmd, capture_output=True, encoding='utf-8', check=True,
            creationflags=_CREATION_FLAGS
        )
        import json
        data = json.loads(result.stdout)

        # Format info
        fmt = data.get("format", {})
        info["duration"] = float(fmt.get("duration", 0))

        # Stream info
        streams = data.get("streams", [])
        if streams:
            s = streams[0]
            info["width"] = int(s.get("width", 0))
            info["height"] = int(s.get("height", 0))
            info["codec"] = s.get("codec_name", "")
            # Parse r_frame_rate "30/1" → 30.0
            fps_str = s.get("r_frame_rate", "0/1")
            if "/" in fps_str:
                num, den = fps_str.split("/")
                info["fps"] = round(int(num) / max(int(den), 1), 2)

    except Exception as e:
        logger.error(f"Error getting video info for {path}: {e}")

    return info
