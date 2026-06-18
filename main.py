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

def _install_excepthook(logger):
    def _hook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        logger.critical("Unhandled exception — app will exit", exc_info=(exc_type, exc_value, exc_tb))
    sys.excepthook = _hook

    def _thread_hook(args):
        if args.exc_type is SystemExit:
            return
        logger.critical(
            "Unhandled exception in thread %s", args.thread.name if args.thread else "?",
            exc_info=(args.exc_type, args.exc_value, args.exc_tb),
        )
    threading.excepthook = _thread_hook

def main():
    logger = logging.getLogger(__name__)
    _install_excepthook(logger)
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
        except Exception:
            logger.exception("ui.run() crashed — forcing shutdown")
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