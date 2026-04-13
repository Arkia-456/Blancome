from commands.base import Command

class HelloCommand(Command):
	def matches(self, text: str) -> bool:
		return "hello" in text
	
	def execute(self, text: str):
		print("You said", text, ". Hello back!")