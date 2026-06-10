from pathlib import Path
import threading
import time
import pygame

class MusicPlayer:
	def __init__(self):
		pygame.mixer.init()
		self._tracks: list[Path] = []
		self._index = 0
		self._playing = False
		self._paused = False
		self._lock = threading.Lock()
		self._watcher = threading.Thread(target=self._watch_end, daemon=True)
		self._watcher.start()

	def _watch_end(self):
		while True:
			time.sleep(0.5)
			with self._lock:
				if self._playing and not self._paused and not pygame.mixer.music.get_busy():
					self._index = (self._index + 1) % len(self._tracks)
					self._play_current()

	def load_playlist(self, playlist_path: Path) -> int:
		tracks = []
		playlist_dir = playlist_path.parent

		with open(playlist_path, encoding="utf-8") as f:
			for line in f:
				line = line.strip()
				if not line or line.startswith("#"):
					continue
				track = Path(line)
				if not track.is_absolute():
					track = playlist_dir / track
				if track.exists():
					tracks.append(track)
				else:
					print("Track not found:", track)

		with self._lock:
			self._tracks = tracks
			self._index = 0

		print(f"Loaded {len(tracks)} tracks from playlist.")
		return len(tracks)

	def play(self):
		with self._lock:
			if not self._tracks:
				print("No tracks loaded to play.")
				return
			self._play_current()

	def pause(self):
		with self._lock:
			pygame.mixer.music.pause()
			self._paused = True

	def unpause(self):
		with self._lock:
			pygame.mixer.music.unpause()
			self._paused = False

	def stop(self):
		with self._lock:
			pygame.mixer.music.stop()
			self._playing = False
			self._paused = False
			print("Music stopped.")

	def next(self):
		with self._lock:
			if not self._tracks:
				return
			self._index = (self._index + 1) % len(self._tracks)
			self._play_current()

	def previous(self):
		with self._lock:
			if not self._tracks:
				return
			self._index = (self._index - 1) % len(self._tracks)
			self._play_current()

	def is_playing(self) -> bool:
		return pygame.mixer.music.get_busy()

	def is_paused(self) -> bool:
		return self._paused

	def _play_current(self):
		track = self._tracks[self._index]
		pygame.mixer.music.load(str(track))
		pygame.mixer.music.play()
		self._playing = True
		self._paused = False

player = MusicPlayer()
