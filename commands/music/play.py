import logging
from commands.base import Command
from config import PLAYLIST_FILES
from assistant.player import player

logger = logging.getLogger(__name__)

class PlayCommand(Command):
	def matches(self, text: str) -> bool:
		return "musique" in text

	def execute(self, text: str):
		playlist_name = text[len("musique"):].strip().upper()

		if playlist_name not in PLAYLIST_FILES:
			logger.warning("Playlist '%s' not found. Available: %s", playlist_name, list(PLAYLIST_FILES.keys()))
			return

		playlist_file = PLAYLIST_FILES[playlist_name]
		logger.info("Loading playlist '%s' from %s.", playlist_name, playlist_file)
		count = player.load_playlist(playlist_file)

		if count == 0:
			logger.warning("No tracks found in playlist '%s'.", playlist_name)
			return

		logger.info("Starting playback of '%s' (%d tracks).", playlist_name, count)
		player.play()