from commands.base import Command
from assistant.music_service import music_service


class NextCommand(Command):
	def matches(self, text: str) -> bool:
		return "suivant" in text

	def execute(self, _text: str):
		music_service.next()