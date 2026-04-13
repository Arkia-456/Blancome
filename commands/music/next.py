from assistant.player import player
from commands.base import Command

class NextCommand(Command):
	def matches(self, text: str) -> bool:
		return "suivant" in text
	
	def execute(self, text: str):
		if player.is_playing():
			print("Next music.")
			player.next()
		else:
			print("No music is currently playing.")