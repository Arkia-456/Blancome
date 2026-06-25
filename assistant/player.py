import logging
import random
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
        self._shuffle = False
        self._shuffle_remaining: list[int] = []
        self._history: list[int] = []
        self._lock = threading.Lock()
        self._watcher = threading.Thread(target=self._watch_end, daemon=True)
        self._watcher.start()

    # ── Internal ─────────────────────────────────────────────────────────

    def _watch_end(self):
        _log = logging.getLogger(__name__)
        while True:
            try:
                time.sleep(0.5)
                with self._lock:
                    if self._playing and not self._paused and not pygame.mixer.music.get_busy():
                        self._advance()
            except Exception:
                _log.exception("Error in music watcher thread")

    def _advance(self):
        """Move to next track. Called with lock held."""
        if self._shuffle:
            if not self._shuffle_remaining:
                self._playing = False
                self._current_info = {}
                return
        else:
            if self._index + 1 >= len(self._tracks):
                self._playing = False
                self._current_info = {}
                return
        self._history.append(self._index)
        if self._shuffle:
            self._index = self._shuffle_remaining.pop(0)
        else:
            self._index += 1
        self._play_current()

    def _play_current(self):
        track = self._tracks[self._index]
        self._current_info = dict(
            self._track_infos[self._index]
            if self._index < len(self._track_infos)
            else self._read_track_info(track)
        )
        self._paused_pos = 0.0
        self._seek_offset = 0.0
        pygame.mixer.music.load(str(track))
        pygame.mixer.music.play()
        self._playing = True
        self._paused = False

    def _reset_shuffle(self):
        """Clear shuffle state. Call with lock held."""
        self._shuffle = False
        self._shuffle_remaining.clear()
        self._history.clear()

    # ── Playlist management ───────────────────────────────────────────────

    def scan_playlist(self, playlist_path: Path) -> list[Path]:
        """Return valid track paths from a playlist without loading metadata."""
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
                    _logger.warning("Track not found: %s", track)
        return tracks

    def load_playlist(self, playlist_path: Path) -> int:
        tracks = self.scan_playlist(playlist_path)
        infos = [self._read_track_info(t) for t in tracks]
        with self._lock:
            self._tracks = tracks
            self._track_infos = infos
            self._index = 0
            self._reset_shuffle()
        _logger.info("Loaded %d tracks from playlist.", len(tracks))
        return len(tracks)

    def set_playlist(self, tracks: list[Path], infos: list[dict]) -> int:
        """Replace the queue with pre-loaded track data."""
        with self._lock:
            self._tracks = list(tracks)
            self._track_infos = list(infos)
            self._index = 0
            self._reset_shuffle()
        _logger.info("Playlist set with %d tracks.", len(tracks))
        return len(tracks)

    def add_tracks_batch(self, tracks: list[Path], infos: list[dict]) -> bool:
        """Bulk-add pre-loaded tracks to the existing queue. Returns True if queue was empty before."""
        with self._lock:
            was_empty = not self._tracks
            base = len(self._tracks)
            self._tracks.extend(tracks)
            self._track_infos.extend(infos)
            if self._shuffle:
                for i in range(base, len(self._tracks)):
                    pos = random.randint(0, len(self._shuffle_remaining))
                    self._shuffle_remaining.insert(pos, i)
        _logger.info("Batch-added %d tracks.", len(tracks))
        return was_empty

    def add_track(self, path: Path) -> bool:
        if not path.exists():
            return False
        info = self._read_track_info(path)
        with self._lock:
            new_index = len(self._tracks)
            self._tracks.append(path)
            self._track_infos.append(info)
            if self._shuffle:
                pos = random.randint(0, len(self._shuffle_remaining))
                self._shuffle_remaining.insert(pos, new_index)
        return True

    def remove_track(self, index: int) -> bool:
        with self._lock:
            if not (0 <= index < len(self._tracks)):
                return False
            self._tracks.pop(index)
            self._track_infos.pop(index)

            if self._shuffle:
                self._shuffle_remaining = [
                    (i - 1 if i > index else i)
                    for i in self._shuffle_remaining if i != index
                ]
                self._history = [
                    (i - 1 if i > index else i)
                    for i in self._history if i != index
                ]

            if not self._tracks:
                pygame.mixer.music.stop()
                self._playing = False
                self._paused = False
                self._current_info = {}
                self._index = 0
                self._reset_shuffle()
            elif index == self._index:
                if self._index >= len(self._tracks):
                    self._index = 0
                self._play_current()
            elif index < self._index:
                self._index -= 1
            return True

    # ── Playback control ──────────────────────────────────────────────────

    def play(self):
        with self._lock:
            if not self._tracks:
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
            self._reset_shuffle()
            _logger.info("Music stopped.")

    def next(self):
        with self._lock:
            if not self._tracks:
                return
            was_paused = self._paused
            if self._shuffle:
                if not self._shuffle_remaining:
                    return
                self._history.append(self._index)
                self._index = self._shuffle_remaining.pop(0)
            else:
                if self._index + 1 >= len(self._tracks):
                    return
                self._history.append(self._index)
                self._index += 1
            self._play_current()
            if was_paused:
                pygame.mixer.music.pause()
                self._paused = True

    def previous(self):
        with self._lock:
            if not self._tracks:
                return
            was_paused = self._paused
            if self._shuffle:
                if not self._history:
                    return
                self._shuffle_remaining.insert(0, self._index)
                self._index = self._history.pop()
            else:
                self._index = (self._index - 1) % len(self._tracks)
            self._play_current()
            if was_paused:
                pygame.mixer.music.pause()
                self._paused = True

    def play_track(self, index: int):
        with self._lock:
            if 0 <= index < len(self._tracks):
                self._history.append(self._index)
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

    # ── Shuffle ───────────────────────────────────────────────────────────

    def toggle_shuffle(self) -> bool:
        with self._lock:
            if self._shuffle:
                self._shuffle = False
                self._shuffle_remaining.clear()
                self._history.clear()
            else:
                self._shuffle = True
                # Keep history intact so pre-shuffle tracks are reachable with previous()
                remaining = list(range(self._index + 1, len(self._tracks)))
                random.shuffle(remaining)
                self._shuffle_remaining = remaining
            return self._shuffle

    def is_shuffle(self) -> bool:
        with self._lock:
            return self._shuffle

    # ── State queries ─────────────────────────────────────────────────────

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

    @staticmethod
    def _read_track_info(path: Path) -> dict:
        try:
            audio = MutagenFile(path, easy=True)
            if audio is None:
                return {}
            return {
                "title": (audio.get("title") or [None])[0],
                "artist": (audio.get("artist") or [None])[0],
                "album":  (audio.get("album")  or [None])[0],
                "duration": getattr(audio.info, "length", None),
            }
        except Exception:
            return {}


player = MusicPlayer()
