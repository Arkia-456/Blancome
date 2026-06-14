import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

FREE_MOBILE_USER = os.getenv("FREE_MOBILE_USER", "")
FREE_MOBILE_API_KEY = os.getenv("FREE_MOBILE_API_KEY", "")

PLAYLIST_FILES = {
    key[len("PLAYLIST_"):]: Path(value)
    for key, value in os.environ.items()
    if key.startswith("PLAYLIST_") and value
}

_shopping_list = os.getenv("SHOPPING_LIST_FILE", "")
SHOPPING_LIST_FILE = Path(_shopping_list) if _shopping_list else None

GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_TOKEN_FILE    = Path("google_token.json")

MICROSOFT_CLIENT_ID  = os.getenv("MICROSOFT_CLIENT_ID", "")
MICROSOFT_TOKEN_FILE = Path("microsoft_token.json")
