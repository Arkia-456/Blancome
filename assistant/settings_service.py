import json
import logging
import config

logger = logging.getLogger(__name__)


class SettingsService:
    def _read(self) -> dict:
        try:
            return json.loads(config.SETTINGS_FILE.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except Exception:
            return {}

    def _write(self, data: dict):
        tmp = config.SETTINGS_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(config.SETTINGS_FILE)
        config.reload()

    # ── Batch save (used by the settings UI) ─────────────────────────────

    def save_all(self, user: str, api_key: str, shopping_path: str, playlists: dict) -> None:
        data = self._read()
        data["free_mobile_user"]    = user
        data["free_mobile_api_key"] = api_key
        data["shopping_list_file"]  = shopping_path
        data["playlists"]           = {k: v for k, v in playlists.items() if k and v}
        self._write(data)
        logger.info("All settings saved.")

    # ── Individual setters (voice-command friendly) ───────────────────────

    def set_free_mobile(self, user: str, api_key: str) -> None:
        data = self._read()
        data["free_mobile_user"]    = user
        data["free_mobile_api_key"] = api_key
        self._write(data)
        logger.info("Free Mobile credentials updated.")

    def set_shopping_list(self, path: str) -> None:
        data = self._read()
        data["shopping_list_file"] = path
        self._write(data)
        logger.info("Shopping list file set to: %s", path)

    def add_playlist(self, name: str, path: str) -> None:
        data = self._read()
        data.setdefault("playlists", {})[name.strip().upper()] = path
        self._write(data)
        logger.info("Playlist '%s' added.", name)

    def remove_playlist(self, name: str) -> None:
        data = self._read()
        data.setdefault("playlists", {}).pop(name.strip().upper(), None)
        self._write(data)
        logger.info("Playlist '%s' removed.", name)


settings_service = SettingsService()
