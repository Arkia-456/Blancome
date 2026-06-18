import logging
import sys
import threading
import time
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
    _t0 = time.perf_counter()

    brain = Brain(require_wake_word=True)
    logger.info("Brain ready — %.3fs", time.perf_counter() - _t0)

    _t1 = time.perf_counter()
    listener = Listener(on_phrase=brain.handle)
    logger.info("Listener ready — %.3fs", time.perf_counter() - _t1)

    if sys.platform == "win32":
        _t2 = time.perf_counter()
        from assistant import ui
        logger.info("UI module imported — %.3fs", time.perf_counter() - _t2)

        threading.Thread(target=listener.start, daemon=True).start()

        _t3 = time.perf_counter()
        logger.info("Launching window... (%.3fs since start)", time.perf_counter() - _t0)
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