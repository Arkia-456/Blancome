import logging
from commands.base import Command
from config import SHOPPING_LIST_FILE
from datetime import datetime

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

		logger.info("Adding '%s' to shopping list.", product)
		try:
			SHOPPING_LIST_FILE.parent.mkdir(parents=True, exist_ok=True)

			with open(SHOPPING_LIST_FILE, "a", encoding="utf-8") as f:
				timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
				f.write(f"- {product} (added {timestamp})\n")

			logger.info("'%s' successfully added to shopping list (%s).", product, SHOPPING_LIST_FILE)
		except Exception as e:
			logger.error("Error writing to shopping list file: %s", e)
	
	def _extract_product(self, text: str) -> str:
		result = text
		all_strips = sorted(STRIP, key=len, reverse=True)
		for phrase in all_strips:
				result = result.replace(phrase, " ")
		return " ".join(result.split()).strip()