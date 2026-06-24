import logging
from pathlib import Path
import threading
import time
import pygame
from mutagen import File as MutagenFile

_logger = logging.getLogger(__name__)

class MusicPlayer:
	def __init__(self):
		_t = time.perf_counter()
		pygame.mixer.init()
		_logger.info("pygame.mixer.init() — %.3fs", time.perf_counter() - _t)
		self._tracks: list[Path] = []
		self._track_infos: list[dict] = []
		self._index = 0
		self._playing = False
		self._paused = False
		self._current_info: dict = {}
		self._paused_pos: float = 0.0
		self._seek_offset: float = 0.0
		self._lock = threading.Lock()
		self._watcher = threading.Thread(target=self._watch_end, daemon=True)
		self._watcher.start()

	def _watch_end(self):
		import logging
		_log = logging.getLogger(__name__)
		while True:
			try:
				time.sleep(0.5)
				with self._lock:
					if self._playing and not self._paused and not pygame.mixer.music.get_busy():
						self._index = (self._index + 1) % len(self._tracks)
						self._play_current()
			except Exception:
				_log.exception("Error in music watcher thread")

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

		infos = [self._read_track_info(t) for t in tracks]

		with self._lock:
			self._tracks = tracks
			self._track_infos = infos
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
			pos_ms = pygame.mixer.music.get_pos()
			if pos_ms >= 0:
				self._paused_pos = self._seek_offset + pos_ms / 1000.0
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
			self._paused_pos = 0.0
			self._current_info = {}
			self._tracks = []
			self._track_infos = []
			self._index = 0
			print("Music stopped.")

	def next(self):
		with self._lock:
			if not self._tracks:
				return
			was_paused = self._paused
			self._index = (self._index + 1) % len(self._tracks)
			self._play_current()
			if was_paused:
				pygame.mixer.music.pause()
				self._paused = True

	def previous(self):
		with self._lock:
			if not self._tracks:
				return
			was_paused = self._paused
			self._index = (self._index - 1) % len(self._tracks)
			self._play_current()
			if was_paused:
				pygame.mixer.music.pause()
				self._paused = True

	def has_tracks(self) -> bool:
		with self._lock:
			return bool(self._tracks)

	def is_playing(self) -> bool:
		return pygame.mixer.music.get_busy()

	def is_paused(self) -> bool:
		return self._paused

	def current_track_info(self) -> dict:
		with self._lock:
			return dict(self._current_info)

	def get_position(self) -> tuple[float, float]:
		with self._lock:
			if not self._tracks:
				return 0.0, 0.0
			duration = float(self._current_info.get("duration") or 0.0)
			if self._paused:
				current = self._paused_pos
			else:
				pos_ms = pygame.mixer.music.get_pos()
				current = (self._seek_offset + pos_ms / 1000.0) if pos_ms >= 0 else self._seek_offset
			return min(current, duration) if duration > 0 else current, duration

	def get_queue(self) -> tuple[list[dict], int]:
		with self._lock:
			result = []
			for i, t in enumerate(self._tracks):
				info = self._track_infos[i] if i < len(self._track_infos) else {}
				result.append({
					"name": t.stem,
					"title": info.get("title"),
					"artist": info.get("artist"),
					"duration": info.get("duration"),
				})
			return result, self._index

	def add_track(self, path: Path) -> bool:
		if not path.exists():
			return False
		info = self._read_track_info(path)
		with self._lock:
			self._tracks.append(path)
			self._track_infos.append(info)
		return True

	def play_track(self, index: int):
		with self._lock:
			if 0 <= index < len(self._tracks):
				self._index = index
				self._play_current()

	def seek(self, seconds: float):
		with self._lock:
			if not self._tracks:
				return
			duration = float(self._current_info.get("duration") or 0.0)
			seconds = max(0.0, min(seconds, duration) if duration > 0 else seconds)
			self._seek_offset = seconds
			pygame.mixer.music.play(start=seconds)
			self._playing = True
			if self._paused:
				pygame.mixer.music.pause()
				self._paused_pos = seconds

	def _play_current(self):
		track = self._tracks[self._index]
		if self._index < len(self._track_infos):
			self._current_info = dict(self._track_infos[self._index])
		else:
			self._current_info = self._read_track_info(track)
		self._paused_pos = 0.0
		self._seek_offset = 0.0
		pygame.mixer.music.load(str(track))
		pygame.mixer.music.play()
		self._playing = True
		self._paused = False

	@staticmethod
	def _read_track_info(path: Path) -> dict:
		try:
			audio = MutagenFile(path, easy=True)
			if audio is None:
				return {}
			return {
				"title": (audio.get("title") or [None])[0],
				"artist": (audio.get("artist") or [None])[0],
				"album": (audio.get("album") or [None])[0],
				"duration": getattr(audio.info, "length", None),
			}
		except Exception:
			return {}

player = MusicPlayer()
