from commands.base import Command
from assistant.music_service import music_service


class StopCommand(Command):
	def matches(self, text: str) -> bool:
		return "stop" in text or "arrête" in text

	def execute(self, _text: str):
		music_service.stop()