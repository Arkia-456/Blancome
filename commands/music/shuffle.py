from commands.base import Command
from assistant.music_service import music_service


class ShuffleCommand(Command):
    def matches(self, text: str) -> bool:
        return "aléatoire" in text

    def execute(self, _text: str):
        music_service.toggle_shuffle()
