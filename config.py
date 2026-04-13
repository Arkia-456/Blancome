import sys
from pathlib import Path

if sys.platform == "win32":
    PLAYLIST_FILES = {
      "MADNESS": Path(r"C:\Users\Aurore\Music\Playlists\Madness.m3u8")
		}
    SHOPPING_LIST_FILE = Path(r"C:\Users\Aurore\Documents\Documents\shopping_list.txt")