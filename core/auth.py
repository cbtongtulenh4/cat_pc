"""
Authentication service — manages token verification and user session.
Uses Singleton pattern so session data is accessible from any widget.
API input is currently FAKE — to be replaced with real endpoint later.
"""
import json
import logging
import time
from pathlib import Path

import requests

from core.config import APP_ROOT
from key_tool import get_key_details

logger = logging.getLogger("auth")

# ── Paths ──
SESSION_FILE = APP_ROOT / ".session.json"

# ── API Configuration ──
API_URL = "https://script.google.com/macros/s/AKfycbz263EEntoO4AoK02NuT0noLLzIdz2x5SjtTBpr_tmGzbDoFqnEpB3l5j8t7flTznyffw/exec"


class AuthService:
    """Singleton authentication service."""

    _instance = None

    def __init__(self):
        # Session data (populated after successful login)
        self.is_authenticated: bool = False
        self.token: str = ""
        self.user_data: dict = {}  # Full response from API (status, user, role, etc.)

    @classmethod
    def instance(cls) -> "AuthService":
        """Get or create the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ── Public API ──

    @property
    def user(self) -> str:
        return self.user_data.get("user", "")

    @property
    def role(self) -> str:
        return self.user_data.get("role", "")

    def login(self, token: str) -> dict:
        """
        Verify a token against the API.

        Returns dict with at minimum:
            {"status": bool, "user": str, ...}
        On network error returns:
            {"status": False, "error": "..."}
        """
        token = token.strip()
        if not token:
            return {"status": False, "error": "Token không được để trống"}

        try:
            result = self._call_api(token)
        except Exception as e:
            logger.error(f"Login API error: {e}")
            return {"status": False, "error": f"Lỗi kết nối: {e}"}

        if result.get("status"):
            # Successful login — store session
            self.is_authenticated = True
            self.token = token
            self.user_data = result
            logger.info(f"Login OK — user={result.get('user')}")
        else:
            logger.warning(f"Login failed — response={result}")
            # Ensure error message is clear
            if "error" not in result and "message" in result:
                result["error"] = result["message"]

        return result

    def logout(self):
        """Clear session and remove saved token."""
        self.is_authenticated = False
        self.token = ""
        self.user_data = {}
        self.clear_saved_token()

    # ── Remember Me ──

    def save_token(self, token: str):
        """Save token to local file for auto-login next time."""
        try:
            data = {"token": token, "saved_at": time.time()}
            SESSION_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
            logger.info("Token saved to session file")
        except Exception as e:
            logger.error(f"Failed to save token: {e}")

    def load_saved_token(self) -> str | None:
        """Load previously saved token, if exists."""
        try:
            if SESSION_FILE.exists():
                data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
                return data.get("token")
        except Exception as e:
            logger.error(f"Failed to load saved token: {e}")
        return None

    def clear_saved_token(self):
        """Remove saved token file."""
        try:
            if SESSION_FILE.exists():
                SESSION_FILE.unlink()
                logger.info("Saved token cleared")
        except Exception:
            pass

    # ── Internal ──

    def _call_api(self, license_key: str) -> dict:
        """Call the official key_tool library function to get full details."""
        logger.info(f"Validating key using key_tool.get_key_details: {license_key[:4]}...")
        
        # This library function now returns the full dict from server
        return get_key_details(
            key=license_key, 
            mode="full", 
            server_url=API_URL
        )
