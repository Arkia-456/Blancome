import logging
from commands.base import Command
from assistant.player import player

logger = logging.getLogger(__name__)

class PauseCommand(Command):
	def matches(self, text: str) -> bool:
		return "pause" in text or "reprend" in text

	def execute(self, text: str):
		if player.is_paused():
			logger.info("Resuming music playback.")
			player.unpause()
		elif player.is_playing():
			logger.info("Pausing music playback.")
			player.pause()
		else:
			logger.info("Pause requested but no music is currently playing.")
