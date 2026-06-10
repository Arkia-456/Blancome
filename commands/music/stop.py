import logging
from assistant.player import player

logger = logging.getLogger(__name__)

class StopCommand:
	def matches(self, text: str) -> bool:
		return "stop" in text or "arrête" in text

	def execute(self, _text: str):
		if player.is_playing():
			logger.info("Stopping music playback.")
			player.stop()
		else:
			logger.info("Stop requested but no music is currently playing.")