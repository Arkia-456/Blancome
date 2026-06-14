import datetime
import logging
import re

from config import MICROSOFT_CLIENT_ID, MICROSOFT_TOKEN_FILE

logger = logging.getLogger(__name__)

_SCOPES = ["Calendars.Read"]
_GRAPH  = "https://graph.microsoft.com/v1.0"

try:
    import msal
    import requests as _requests
    _DEPS_AVAILABLE = True
except ImportError:
    _DEPS_AVAILABLE = False


class MicrosoftCalendarService:
    def __init__(self):
        self._app   = None
        self._cache = None

    def _get_app(self):
        if not _DEPS_AVAILABLE:
            raise RuntimeError("msal package not installed. Run: pip install msal requests")
        if not MICROSOFT_CLIENT_ID:
            raise RuntimeError("MICROSOFT_CLIENT_ID not set in .env")
        if self._app is None:
            self._cache = msal.SerializableTokenCache()
            if MICROSOFT_TOKEN_FILE.exists():
                self._cache.deserialize(MICROSOFT_TOKEN_FILE.read_text(encoding="utf-8"))
            self._app = msal.PublicClientApplication(
                MICROSOFT_CLIENT_ID,
                authority="https://login.microsoftonline.com/common",
                token_cache=self._cache,
            )
        return self._app

    def _acquire_token(self) -> str:
        app      = self._get_app()
        result   = None
        accounts = app.get_accounts()
        if accounts:
            result = app.acquire_token_silent(_SCOPES, account=accounts[0])
        if not result:
            result = app.acquire_token_interactive(_SCOPES)
        if "access_token" not in result:
            raise RuntimeError(
                "Authentification Microsoft échouée : "
                + result.get("error_description", result.get("error", "erreur inconnue"))
            )
        if self._cache and self._cache.has_state_changed:
            MICROSOFT_TOKEN_FILE.write_text(self._cache.serialize(), encoding="utf-8")
            logger.info("Microsoft token saved to %s.", MICROSOFT_TOKEN_FILE)
        return result["access_token"]

    def get_events(self, start: datetime.date, end: datetime.date) -> list[dict]:
        token   = self._acquire_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Prefer": 'outlook.timezone="UTC"',
        }
        params  = {
            "startDateTime": datetime.datetime(start.year, start.month, start.day).strftime("%Y-%m-%dT%H:%M:%S"),
            "endDateTime":   datetime.datetime(end.year, end.month, end.day, 23, 59, 59).strftime("%Y-%m-%dT%H:%M:%S"),
            "$select":       "subject,start,end,isAllDay",
            "$orderby":      "start/dateTime",
            "$top":          "100",
        }
        resp = _requests.get(f"{_GRAPH}/me/calendarView", headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        raw = resp.json().get("value", [])
        logger.info("Fetched %d event(s) from Microsoft Calendar.", len(raw))
        return [self._normalize(ev) for ev in raw]

    @staticmethod
    def _normalize(ev: dict) -> dict:
        """Convert a Microsoft Graph event to Google Calendar-compatible format."""
        def _clean(s: str) -> str:
            # Strip sub-second precision and normalise 'Z' so fromisoformat() works on all Python versions
            return re.sub(r"\.\d+", "", s).replace("Z", "+00:00")

        start = ev.get("start", {})
        end   = ev.get("end",   {})
        if ev.get("isAllDay"):
            return {
                "summary": ev.get("subject", "(Sans titre)"),
                "start":   {"date": start.get("dateTime", "")[:10]},
                "end":     {"date": end.get("dateTime",   "")[:10]},
            }
        return {
            "summary": ev.get("subject", "(Sans titre)"),
            "start":   {"dateTime": _clean(start.get("dateTime", ""))},
            "end":     {"dateTime": _clean(end.get("dateTime",   ""))},
        }


microsoft_calendar_service = MicrosoftCalendarService()
