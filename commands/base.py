from abc import ABC, abstractmethod

class Command(ABC):
	@abstractmethod
	def matches(self, text: str) -> bool:
		pass
	
	@abstractmethod
	def execute(self, text: str):
		pass