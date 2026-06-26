import logging
import sys
import threading
import time
from pathlib import Path

import sounddevice
import queue
import json
from vosk import KaldiRecognizer, Model

logger = logging.getLogger(__name__)

class Listener:
    def __init__(self, on_phrase):
        self._running = False
        self._ready = False
        self._audio_queue = queue.Queue()
        self._model = None
        self._recognizer = None
        self._on_phrase = on_phrase

    @property
    def ready(self) -> bool:
        return self._ready

    def load_model(self):
        """Load the Vosk model. Blocking — call from a background thread."""
        _t = time.perf_counter()
        if getattr(sys, "frozen", False):
            _model_path = str(Path(sys._MEIPASS) / "models/vosk-model")
        else:
            _model_path = "models/vosk-model"
        self._model = Model(_model_path)
        logger.info("Vosk model loaded — %.3fs", time.perf_counter() - _t)
        _t = time.perf_counter()
        self._recognizer = KaldiRecognizer(self._model, 16000)
        logger.info("KaldiRecognizer ready — %.3fs", time.perf_counter() - _t)
        self._ready = True

    def start(self):
        if not self._ready:
            raise RuntimeError("Listener.start() called before load_model() completed")
        self._running = True
        with sounddevice.RawInputStream(
            samplerate=16000,
            blocksize=8000,
            dtype="int16",
            channels=1,
            callback=self._audio_callback
        ):
            logger.info("Listening...")
            self._process_loop()

    def stop(self):
        self._running = False
        logger.info("Stopped listening.")

    def _audio_callback(self, indata, frames, time, status):
        if status:
            logger.warning("Audio stream status: %s", status)
        self._audio_queue.put(bytes(indata))

    def _process_loop(self):
        while self._running:
            data = self._audio_queue.get()
            if self._recognizer.AcceptWaveform(data):
                result = json.loads(self._recognizer.Result())
                text = result.get("text", "").strip()
                if text:
                    logger.debug("Recognized: %s", text)
                    threading.Thread(
                        target=self._on_phrase, args=(text,), daemon=True
                    ).start()
