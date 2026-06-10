import logging
import urllib.parse
import requests
from commands.base import Command
from config import SHOPPING_LIST_FILE, FREE_MOBILE_USER, FREE_MOBILE_API_KEY

TRIGGER_WORDS = ["envoie", "envoyer"]

logger = logging.getLogger(__name__)

class SendSmsCommand(Command):
    def matches(self, text: str) -> bool:
        t = text.lower()
        has_trigger = any(w in t for w in TRIGGER_WORDS)
        has_list = "liste" in t
        return has_trigger and has_list

    def execute(self, text: str):
        try:
            with open(SHOPPING_LIST_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except FileNotFoundError:
            logger.warning("Shopping list file not found at %s.", SHOPPING_LIST_FILE)
            return

        items = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith("- "):
                line = line[2:]
            if " (added " in line:
                line = line[:line.index(" (added ")]
            items.append(line)

        if not items:
            logger.warning("Shopping list is empty, nothing to send.")
            return

        logger.info("Sending %d item(s) via Free Mobile SMS API.", len(items))
        message = "Liste de courses :\n" + "\n".join(f"- {item}" for item in items)

        encoded_message = urllib.parse.quote(message)
        url = (
            f"https://smsapi.free-mobile.fr/sendmsg"
            f"?user={FREE_MOBILE_USER}&pass={FREE_MOBILE_API_KEY}&msg={encoded_message}"
        )

        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                SHOPPING_LIST_FILE.write_text("", encoding="utf-8")
                logger.info("SMS sent successfully (%d items). Shopping list cleared.", len(items))
            elif response.status_code == 403:
                logger.error("SMS failed: SMS option not enabled or invalid credentials (HTTP 403).")
            elif response.status_code == 500:
                logger.error("SMS failed: Free Mobile server error (HTTP 500).")
            else:
                logger.error("SMS failed: unexpected HTTP %d.", response.status_code)
        except Exception as e:
            logger.error("Exception while calling Free Mobile API: %s", e)
