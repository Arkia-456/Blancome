from commands.base import Command
from commands.hello import HelloCommand

class Brain:
	def __init__(self):
		self._commands: list[Command] = [HelloCommand()]
		print("Brain initialized with ", len(self._commands), " commands.")

	def handle(self, text: str):
		text = text.lower().strip()

		for command in self._commands:
			if command.matches(text):
				command.execute(text)
				return
		
		print("No command matched for: '", text, "'")