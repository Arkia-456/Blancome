from commands.base import Command
from assistant.music_service import music_service


class PauseCommand(Command):
	def matches(self, text: str) -> bool:
		return "pause" in text or "reprend" in text

	def execute(self, _text: str):
		music_service.toggle_pause()
