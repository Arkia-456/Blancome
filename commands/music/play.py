import logging
from commands.base import Command
import config
from assistant.music_service import music_service

logger = logging.getLogger(__name__)

TRIGGERS = ["musique", "lance"]

class PlayCommand(Command):
	def matches(self, text: str) -> bool:
		return any(t in text for t in TRIGGERS)

	def execute(self, text: str):
		trigger = next(t for t in TRIGGERS if t in text)
		playlist_name = text[text.index(trigger) + len(trigger):].strip().upper()

		if playlist_name not in config.PLAYLIST_FILES:
			logger.warning("Playlist '%s' not found. Available: %s", playlist_name, list(config.PLAYLIST_FILES.keys()))
			return

		logger.info("Loading playlist '%s' from %s.", playlist_name, config.PLAYLIST_FILES[playlist_name])
		music_service.load_playlist(config.PLAYLIST_FILES[playlist_name])