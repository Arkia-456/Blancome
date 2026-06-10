import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

FREE_MOBILE_USER = os.getenv("FREE_MOBILE_USER", "")
FREE_MOBILE_API_KEY = os.getenv("FREE_MOBILE_API_KEY", "")

if sys.platform == "win32":
    PLAYLIST_FILES = {
      "MADNESS": Path(r"C:\Users\Aurore\Music\Playlists\Madness.m3u8")
		}
    SHOPPING_LIST_FILE = Path(r"C:\Users\Aurore\Documents\Documents\shopping_list.txt")