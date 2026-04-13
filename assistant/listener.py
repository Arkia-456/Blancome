import threading

import sounddevice
import queue
import json
from vosk import KaldiRecognizer, Model

class Listener:
	def __init__(self, on_phrase):
		self._running = False
		self._audio_queue = queue.Queue()
		self._model = Model("models/vosk-model")
		self._recognizer = KaldiRecognizer(self._model, 16000)
		self._on_phrase = on_phrase

	def start(self):
		self._running = True
		with sounddevice.RawInputStream(
			samplerate=16000,
      blocksize=8000,
      dtype="int16",
      channels=1,
      callback=self._audio_callback
		):
			print("Listening...")
			self._process_loop()

	def stop(self):
		self._running = False
		print("Stopped listening.")
	
	def _audio_callback(self, indata, frames, time, status):
		if status:
			print("Audio stream status: ", status)
		self._audio_queue.put(bytes(indata))
	
	def _process_loop(self):
		while self._running:
			data = self._audio_queue.get()
			if self._recognizer.AcceptWaveform(data):
				result = json.loads(self._recognizer.Result())
				text = result.get("text", "").strip()
				if text:
					print("Recognized:", text)
					threading.Thread(
            target=self._on_phrase, args=(text,), daemon=True
          ).start()