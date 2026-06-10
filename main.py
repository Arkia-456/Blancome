import logging
from assistant.listener import Listener
from assistant.brain import Brain

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)-8s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)

def main():
    logger = logging.getLogger(__name__)
    logger.info("Starting Blancassist...")
    brain = Brain(require_wake_word=True)
    listener = Listener(on_phrase=brain.handle)

    try:
        listener.start()
    except KeyboardInterrupt:
        listener.stop()
        logger.info("Blancassist stopped.")

if __name__ == "__main__":
    main()