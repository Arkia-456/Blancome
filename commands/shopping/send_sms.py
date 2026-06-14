import logging
from commands.base import Command
from assistant.shopping_service import shopping_service

TRIGGER_WORDS = ["envoie", "envoyer"]

logger = logging.getLogger(__name__)


class SendSmsCommand(Command):
    def matches(self, text: str) -> bool:
        t = text.lower()
        return any(w in t for w in TRIGGER_WORDS) and "liste" in t

    def execute(self, text: str):
        shopping_service.send_list()
