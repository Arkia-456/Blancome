from commands.base import Command
from assistant.music_service import music_service


class PreviousCommand(Command):
	def matches(self, text: str) -> bool:
		return "précédent" in text

	def execute(self, _text: str):
		music_service.previous()
