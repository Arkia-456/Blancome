import logging
from commands.base import Command
from assistant.player import player

logger = logging.getLogger(__name__)

class PreviousCommand(Command):
	def matches(self, text: str) -> bool:
		return "précédent" in text

	def execute(self, _text: str):
		if player.is_playing():
			logger.info("Going to previous track.")
			player.previous()
		else:
			logger.info("Previous requested but no music is currently playing.")
