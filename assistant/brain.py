import logging
from commands.base import Command
from commands.hello import HelloCommand
from commands.music.play import PlayCommand
from commands.music.stop import StopCommand
from commands.music.next import NextCommand
from commands.shopping.add import AddCommand
from commands.shopping.send_sms import SendSmsCommand
from commands.shopping.list import ListCommand

WAKE_WORDS = ["blanco"]

logger = logging.getLogger(__name__)

class Brain:
	def __init__(self, require_wake_word: bool = False):
		self._require_wake_word = require_wake_word
		self._commands: list[Command] = [HelloCommand(), PlayCommand(), StopCommand(), NextCommand(), AddCommand(), SendSmsCommand(), ListCommand()]
		logger.info("Brain initialized with %d commands.", len(self._commands))

	def handle(self, text: str):
		text = text.lower().strip()

		if self._require_wake_word:
			triggered, text = self._strip_wake_word(text)
			if not triggered:
				logger.debug("Wake word not detected in: '%s'. Ignoring.", text)
				return

		logger.info("Processing command: '%s'", text)

		for command in self._commands:
			if command.matches(text):
				logger.info("Matched command: %s", type(command).__name__)
				command.execute(text)
				return

		logger.warning("No command matched for: '%s'", text)

	def _strip_wake_word(self, text: str):
		words = text.split()
		for i, word in enumerate(words):
			if word in WAKE_WORDS:
				return True, " ".join(words[i + 1:]).strip()
		return False, text