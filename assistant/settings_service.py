import logging
import re
from pathlib import Path
from dotenv import set_key, unset_key
import config

logger = logging.getLogger(__name__)

_ENV_PATH = config.APP_DIR / ".env"


class SettingsService:
    """Reads and writes .env settings.

    Each method is self-contained so it can be called from a voice command
    without going through the UI.
    """

    # ── Individual setters (voice-command friendly) ──────────────────────

    def set_free_mobile(self, user: str, api_key: str) -> None:
        set_key(_ENV_PATH, "FREE_MOBILE_USER", user)
        set_key(_ENV_PATH, "FREE_MOBILE_API_KEY", api_key)
        config.reload()
        logger.info("Free Mobile credentials updated.")

    def set_shopping_list(self, path: str) -> None:
        set_key(_ENV_PATH, "SHOPPING_LIST_FILE", path)
        config.reload()
        logger.info("Shopping list file set to: %s", path)

    def add_playlist(self, name: str, path: str) -> None:
        set_key(_ENV_PATH, f"PLAYLIST_{name.strip().upper()}", path)
        config.reload()
        logger.info("Playlist '%s' added.", name)

    def remove_playlist(self, name: str) -> None:
        unset_key(_ENV_PATH, f"PLAYLIST_{name.strip().upper()}")
        config.reload()
        logger.info("Playlist '%s' removed.", name)

    # ── Batch save (used by the settings UI) ────────────────────────────

    def save_all(
        self,
        user: str,
        api_key: str,
        shopping_path: str,
        playlists: dict,
    ) -> None:
        """Write all settings in a single atomic file operation.

        Calling set_key() repeatedly causes PermissionError on Windows because
        each call renames a temp file onto .env, and Windows briefly holds a
        lock on the file between renames. Writing once avoids this entirely.
        """
        updates = {
            "FREE_MOBILE_USER":    user,
            "FREE_MOBILE_API_KEY": api_key,
            "SHOPPING_LIST_FILE":  shopping_path,
        }
        for name, path in playlists.items():
            if name and path:
                updates[f"PLAYLIST_{name}"] = path

        # Any existing PLAYLIST_ key not present in updates should be removed.
        to_remove = {
            k for k in self._read_keys() if k.startswith("PLAYLIST_") and k not in updates
        }

        self._atomic_write(updates, to_remove)
        config.reload()
        logger.info("All settings saved.")

    # ── Internal helpers ─────────────────────────────────────────────────

    _KEY_RE = re.compile(r'^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=')

    def _read_keys(self) -> list:
        try:
            lines = _ENV_PATH.read_text(encoding="utf-8").splitlines()
        except FileNotFoundError:
            return []
        keys = []
        for line in lines:
            m = self._KEY_RE.match(line)
            if m:
                keys.append(m.group(1))
        return keys

    @staticmethod
    def _quote(value: str) -> str:
        return f'"{value}"' if " " in value or "\t" in value else value

    def _atomic_write(self, updates: dict, to_remove: set) -> None:
        """Read .env, apply all updates/removals in one pass, write once."""
        try:
            lines = _ENV_PATH.read_text(encoding="utf-8").splitlines(keepends=True)
        except FileNotFoundError:
            lines = []

        handled: set = set()
        result: list = []

        for line in lines:
            m = self._KEY_RE.match(line)
            if m:
                key = m.group(1)
                if key in to_remove:
                    handled.add(key)
                    continue  # drop the line
                if key in updates:
                    result.append(f"{key}={self._quote(updates[key])}\n")
                    handled.add(key)
                    continue
            result.append(line)

        # Append keys that were not already in the file
        for key, val in updates.items():
            if key not in handled:
                result.append(f"{key}={self._quote(val)}\n")

        tmp = _ENV_PATH.with_suffix(".tmp_save")
        tmp.write_text("".join(result), encoding="utf-8")
        tmp.replace(_ENV_PATH)


settings_service = SettingsService()
