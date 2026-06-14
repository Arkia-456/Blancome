import datetime
import logging

from config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_TOKEN_FILE

logger = logging.getLogger(__name__)

_SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    _DEPS_AVAILABLE = True
except ImportError:
    _DEPS_AVAILABLE = False


class CalendarService:
    def __init__(self):
        self._service = None

    def _build_service(self):
        if not _DEPS_AVAILABLE:
            raise RuntimeError(
                "Google API packages are not installed. "
                "Run: pip install google-api-python-client google-auth-oauthlib"
            )
        if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
            raise RuntimeError(
                "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set in your .env file."
            )

        creds = None
        if GOOGLE_TOKEN_FILE.exists():
            creds = Credentials.from_authorized_user_file(str(GOOGLE_TOKEN_FILE), _SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                client_config = {
                    "installed": {
                        "client_id": GOOGLE_CLIENT_ID,
                        "client_secret": GOOGLE_CLIENT_SECRET,
                        "redirect_uris": ["http://localhost"],
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                    }
                }
                flow = InstalledAppFlow.from_client_config(client_config, _SCOPES)
                creds = flow.run_local_server(port=0)
            GOOGLE_TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
            logger.info("Google Calendar token saved to %s.", GOOGLE_TOKEN_FILE)

        return build("calendar", "v3", credentials=creds)

    def _get_service(self):
        if self._service is None:
            self._service = self._build_service()
        return self._service

    def get_events(self, start: datetime.date, end: datetime.date) -> list[dict]:
        """Return events from the primary calendar between `start` and `end` (inclusive)."""
        service  = self._get_service()
        time_min = datetime.datetime(start.year, start.month, start.day).isoformat() + "Z"
        time_max = datetime.datetime(end.year, end.month, end.day, 23, 59, 59).isoformat() + "Z"
        result = service.events().list(
            calendarId="primary",
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        events = result.get("items", [])
        logger.info("Fetched %d event(s) from Google Calendar.", len(events))
        return events


calendar_service = CalendarService()
