from commands.base import Command
from config import PLAYLIST_FILES
from assistant.player import player

class PlayCommand(Command):
	def matches(self, text: str) -> bool:
		return "musique" in text
	
	def execute(self, text: str):
		playlist_name = text[len("musique"):].strip().upper()

		if playlist_name not in PLAYLIST_FILES:
			print(f"Playlist '{playlist_name}' not found.")
			return

		PLAYLIST_FILE = PLAYLIST_FILES[playlist_name]

		count = player.load_playlist(PLAYLIST_FILE)

		if count == 0:
			print("No tracks found in playlist.")
			return
		
		print(f"Loaded {count} tracks from playlist {playlist_name}.")	
		player.play()