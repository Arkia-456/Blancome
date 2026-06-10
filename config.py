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
