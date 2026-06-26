import logging
import urllib.parse
import requests
from datetime import datetime
import config

logger = logging.getLogger(__name__)


class ShoppingService:
    def _is_configured(self) -> bool:
        if config.SHOPPING_LIST_FILE is None:
            logger.error("SHOPPING_LIST_FILE is not configured. Set it in Settings.")
            return False
        return True

    def get_items(self) -> list[str]:
        if not self._is_configured():
            return []
        try:
            with open(config.SHOPPING_LIST_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except FileNotFoundError:
            return []

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
        return items

    def remove_item(self, product: str):
        if not self._is_configured():
            return
        try:
            with open(config.SHOPPING_LIST_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except FileNotFoundError:
            return
        new_lines = []
        removed = False
        for line in lines:
            if not removed:
                cleaned = line.strip()
                if cleaned.startswith("- "):
                    cleaned = cleaned[2:]
                if " (added " in cleaned:
                    cleaned = cleaned[: cleaned.index(" (added ")]
                if cleaned == product:
                    removed = True
                    continue
            new_lines.append(line)
        with open(config.SHOPPING_LIST_FILE, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        if removed:
            logger.info("Removed '%s' from shopping list.", product)

    def send_list(self) -> bool:
        if not self._is_configured():
            return False
        items = self.get_items()
        if not items:
            logger.warning("Shopping list is empty, nothing to send.")
            return False

        message = "Liste de courses :\n" + "\n".join(f"- {item}" for item in items)
        url = (
            f"https://smsapi.free-mobile.fr/sendmsg"
            f"?user={config.FREE_MOBILE_USER}&pass={config.FREE_MOBILE_API_KEY}"
            f"&msg={urllib.parse.quote(message)}"
        )
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                config.SHOPPING_LIST_FILE.write_text("", encoding="utf-8")
                logger.info("SMS sent (%d items). Shopping list cleared.", len(items))
                return True
            logger.error("SMS failed: HTTP %d.", response.status_code)
            return False
        except Exception as e:
            logger.error("Exception calling Free Mobile API: %s", e)
            return False

    def add_item(self, product: str):
        if not self._is_configured():
            return
        config.SHOPPING_LIST_FILE.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        with open(config.SHOPPING_LIST_FILE, "a", encoding="utf-8") as f:
            f.write(f"- {product} (added {timestamp})\n")
        logger.info("Added '%s' to shopping list.", product)


shopping_service = ShoppingService()
