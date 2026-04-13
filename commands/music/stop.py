from assistant.player import player

class StopCommand:
	def matches(self, text: str) -> bool:
		return "stop" in text or "arrête" in text
	
	def execute(self, text: str):
		if player.is_playing():
			print("Stopping music playback.")
			player.stop()
		else:
			print("No music is currently playing.")