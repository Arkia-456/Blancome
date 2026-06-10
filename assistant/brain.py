from commands.base import Command
from commands.hello import HelloCommand
from commands.music.play import PlayCommand
from commands.music.stop import StopCommand
from commands.music.next import NextCommand
from commands.shopping.add import AddCommand

WAKE_WORDS = ["blanco"]

class Brain:
	def __init__(self, require_wake_word: bool = False):
		self._require_wake_word = require_wake_word
		self._commands: list[Command] = [HelloCommand(), PlayCommand(), StopCommand(), NextCommand(), AddCommand()]
		print("Brain initialized with ", len(self._commands), " commands.")

	def handle(self, text: str):
		text = text.lower().strip()

		if self._require_wake_word:
			triggered, text = self._strip_wake_word(text)
			if not triggered:
				print("Wake word not detected in: '", text, "'. Ignoring.")
				return
			
		print("Processing command: '", text, "'")

		for command in self._commands:
			if command.matches(text):
				command.execute(text)
				return
		
		print("No command matched for: '", text, "'")

	def _strip_wake_word(self, text: str):
		words = text.split()
		for i, word in enumerate(words):
			if word in WAKE_WORDS:
				return True, " ".join(words[i + 1:]).strip()
		return False, text