import logging
import sys
import threading
from assistant.listener import Listener
from assistant.brain import Brain

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)-8s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)

def main():
    logger = logging.getLogger(__name__)
    logger.info("Starting Blancome...")
    brain = Brain(require_wake_word=True)
    listener = Listener(on_phrase=brain.handle)

    if sys.platform == "win32":
        from assistant import ui
        threading.Thread(target=listener.start, daemon=True).start()
        try:
            ui.run(on_close=listener.stop)
        except KeyboardInterrupt:
            listener.stop()
        logger.info("Blancome stopped.")
    else:
        try:
            listener.start()
        except KeyboardInterrupt:
            listener.stop()
            logger.info("Blancome stopped.")

if __name__ == "__main__":
    main()