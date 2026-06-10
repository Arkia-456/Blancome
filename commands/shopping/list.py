import logging
from commands.base import Command
from config import SHOPPING_LIST_FILE

ADD_TRIGGERS = ["ajoute", "rajoute", "mets", "note"]
SEND_TRIGGERS = ["envoie", "envoyer"]

logger = logging.getLogger(__name__)


class ListCommand(Command):
    def matches(self, text: str) -> bool:
        t = text.lower()
        words = t.split()

        if any(w in words for w in ADD_TRIGGERS):
            return False
        if any(w in t for w in SEND_TRIGGERS):
            return False

        has_list = "liste" in t
        has_context = any(w in t for w in ["quoi", "acheter", "achats", "courses"])
        return has_list and has_context

    def execute(self, text: str):
        try:
            with open(SHOPPING_LIST_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except FileNotFoundError:
            logger.info("Shopping list is empty (file not found).")
            return

        items = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith("- "):
                line = line[2:]
            if " (added " in line:
                line = line[: line.index(" (added ")]
            items.append(line)

        if not items:
            logger.info("Shopping list is empty.")
            return

        logger.info("Shopping list (%d item(s)):", len(items))
        for item in items:
            logger.info("  - %s", item)
