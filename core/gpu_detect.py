"""
GPU hardware encoder detection.
Migrated from demo_server/app.py — _detect_gpu_encoder, get_hardware_encoder, get_encoder_preset.
"""
import os
import subprocess
import logging

logger = logging.getLogger("gpu_detect")

# --- GPU encoder cache (detect once, reuse forever) ---
_cached_gpu_encoder = None
_gpu_detected = False


def _detect_gpu_encoder() -> str | None:
    """Detect GPU encoder once and cache the result."""
    global _cached_gpu_encoder, _gpu_detected
    if _gpu_detected:
        return _cached_gpu_encoder
    _gpu_detected = True

    if os.name != 'nt':
        return None

    try:
        result = subprocess.run(
            ["wmic", "path", "win32_VideoController", "get", "name"],
            capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        output = result.stdout.lower()
        if "nvidia" in output:
            _cached_gpu_encoder = "h264_nvenc"
        elif "amd" in output or "radeon" in output:
            _cached_gpu_encoder = "h264_amf"
        elif "intel" in output:
            _cached_gpu_encoder = "h264_qsv"
        logger.info(f"GPU encoder detected: {_cached_gpu_encoder}")
    except Exception:
        pass

    return _cached_gpu_encoder


def get_hardware_encoder(ext: str) -> str | None:
    """Get the hardware encoder name for a given output format extension."""
    if ext.lower() not in ['mp4', 'mkv', 'avi', 'mov', 'flv']:
        return None
    return _detect_gpu_encoder()


def get_encoder_preset(encoder_name: str | None) -> list[str]:
    """Return the fastest preset args for the given encoder."""
    if encoder_name == "h264_nvenc":
        return ["-preset", "p1"]
    elif encoder_name == "h264_amf":
        return ["-quality", "speed"]
    elif encoder_name == "h264_qsv":
        return ["-preset", "veryfast"]
    else:
        # CPU libx264 — ultrafast for maximum speed
        return ["-preset", "ultrafast"]
