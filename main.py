import logging
import sys
import threading
import time
from assistant.brain import Brain
from assistant.listener import Listener

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

    if sys.platform == "win32":
        # QApplication must exist before any Qt widget — create it before heavy imports
        from PyQt6.QtWidgets import QApplication
        _app = QApplication.instance() or QApplication(sys.argv)

        from assistant.splash import AppSplash
        _splash = AppSplash()
        _splash.show()
        _app.processEvents()

        _splash.step(5)
        brain = Brain(require_wake_word=True)
        logger.info("Brain ready — %.3fs", time.perf_counter() - _t0)

        _splash.step(10)
        listener = Listener(on_phrase=brain.handle)
        logger.info("Listener created — %.3fs", time.perf_counter() - _t0)

        _t2 = time.perf_counter()
        _splash.step(15)
        from assistant import ui
        logger.info("UI module imported — %.3fs", time.perf_counter() - _t2)

        logger.info("Launching window... (%.3fs since start)", time.perf_counter() - _t0)
        try:
            ui.run(listener=listener, on_close=listener.stop, splash=_splash)
        except KeyboardInterrupt:
            listener.stop()
        except Exception:
            logger.exception("ui.run() crashed — forcing shutdown")
            listener.stop()
        logger.info("Blancome stopped.")

    else:
        brain = Brain(require_wake_word=True)
        logger.info("Brain ready — %.3fs", time.perf_counter() - _t0)

        listener = Listener(on_phrase=brain.handle)
        logger.info("Listener created — %.3fs", time.perf_counter() - _t0)

        def _load_and_run():
            try:
                logger.info("Loading voice model in background…")
                listener.load_model()
                logger.info("Voice model ready — starting listener")
                listener.start()
            except Exception:
                logger.exception("Listener crashed")

        t = threading.Thread(target=_load_and_run, daemon=False, name="listener")
        t.start()
        try:
            t.join()
        except KeyboardInterrupt:
            listener.stop()
            t.join()
            logger.info("Blancome stopped.")

if __name__ == "__main__":
    main()
