import json
import os
import sys
from pathlib import Path

# Absolute base dir: next to the exe when packaged, project root in development.
# Used for user files (settings, OAuth tokens) that live outside the bundle.
APP_DIR: Path = (
    Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
)

SETTINGS_FILE:       Path = APP_DIR / "settings.json"
GOOGLE_TOKEN_FILE:   Path = APP_DIR / "google_token.json"
MICROSOFT_TOKEN_FILE: Path = APP_DIR / "microsoft_token.json"

_DEFAULTS: dict = {
    "free_mobile_user":    "",
    "free_mobile_api_key": "",
    "shopping_list_file":  "",
    "playlists":           {},
    "google_client_id":    "",
    "google_client_secret": "",
    "microsoft_client_id": "",
}


def _load() -> dict:
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8-sig"))
        return {**_DEFAULTS, **data}
    except FileNotFoundError:
        return dict(_DEFAULTS)
    except Exception:
        return dict(_DEFAULTS)


_s = _load()

FREE_MOBILE_USER     = _s["free_mobile_user"]
FREE_MOBILE_API_KEY  = _s["free_mobile_api_key"]
SHOPPING_LIST_FILE   = Path(_s["shopping_list_file"]) if _s["shopping_list_file"] else None
PLAYLIST_FILES       = {k: Path(v) for k, v in _s.get("playlists", {}).items() if v}
GOOGLE_CLIENT_ID     = _s["google_client_id"]
GOOGLE_CLIENT_SECRET = _s["google_client_secret"]
MICROSOFT_CLIENT_ID  = _s["microsoft_client_id"]


def reload():
    """Re-read settings.json and update all module-level values in place."""
    m = sys.modules[__name__]
    s = _load()
    m.FREE_MOBILE_USER     = s["free_mobile_user"]
    m.FREE_MOBILE_API_KEY  = s["free_mobile_api_key"]
    m.SHOPPING_LIST_FILE   = Path(s["shopping_list_file"]) if s["shopping_list_file"] else None
    m.PLAYLIST_FILES       = {k: Path(v) for k, v in s.get("playlists", {}).items() if v}
    m.GOOGLE_CLIENT_ID     = s["google_client_id"]
    m.GOOGLE_CLIENT_SECRET = s["google_client_secret"]
    m.MICROSOFT_CLIENT_ID  = s["microsoft_client_id"]
