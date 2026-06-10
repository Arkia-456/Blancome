import urllib.parse
import requests
from commands.base import Command
from config import SHOPPING_LIST_FILE, FREE_MOBILE_USER, FREE_MOBILE_API_KEY

TRIGGER_WORDS = ["envoie", "envoyer"]

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
            print("La liste de courses est vide.")
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
            print("La liste de courses est vide.")
            return

        message = "Liste de courses :\n" + "\n".join(f"- {item}" for item in items)

        encoded_message = urllib.parse.quote(message)
        url = (
            f"https://smsapi.free-mobile.fr/sendmsg"
            f"?user={FREE_MOBILE_USER}&pass={FREE_MOBILE_API_KEY}&msg={encoded_message}"
        )

        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                print("Liste envoyée par SMS.")
            elif response.status_code == 403:
                print("Échec : option SMS non activée ou identifiant/clé API incorrects.")
            elif response.status_code == 500:
                print("Erreur serveur Free Mobile, réessayez plus tard.")
            else:
                print(f"Échec de l'envoi SMS : HTTP {response.status_code}")
        except Exception as e:
            print("Erreur lors de l'envoi du SMS :", e)
