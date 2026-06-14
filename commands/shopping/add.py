import logging
import re
from commands.base import Command
from assistant.shopping_service import shopping_service

logger = logging.getLogger(__name__)

TRIGGER_PHRASES = [
	"ajoute",
	"rajoute",
	"mets",
	"liste de courses"
]

TRIGGERS = ["ajoute", "rajoute", "mets", "note"]
LIST_WORDS = ["liste", "courses", "achats"]

STRIP = [
    "sur la liste de courses", "sur ma liste de courses",
    "a la liste de courses",
    "dans la liste de courses",
    "sur la liste", "sur ma liste",
    "dans la liste", "a la liste",
    "liste de courses", "liste",
    "ajoute", "rajoute", "mets", "achete", "note",
    "de la ", "des ", "du ", "de l'", "de l\u2019",
    "le ", "la ", "les ", "un ", "une ",
]

class AddCommand(Command):
	def matches(self, text: str) -> bool:
		words = text.lower().split()
		has_trigger = any(t in words for t in TRIGGERS)
		has_list = any(w in text.lower() for w in LIST_WORDS)
		return has_trigger and has_list
	
	def execute(self, text: str):
		product = self._extract_product(text.lower().strip())

		if not product:
			logger.warning("No product could be extracted from: '%s'", text)
			return

		shopping_service.add_item(product)
	
	def _extract_product(self, text: str) -> str:
		result = text
		for phrase in sorted(STRIP, key=len, reverse=True):
			if phrase.endswith(" "):
				result = re.sub(r'\b' + re.escape(phrase.strip()) + r'\b', " ", result)
			else:
				result = result.replace(phrase, " ")
		return " ".join(result.split()).strip()