import logging
from pathlib import Path
from assistant.player import player

logger = logging.getLogger(__name__)


class MusicService:
    def toggle_pause(self):
        if player.is_paused():
            logger.info("Resuming music playback.")
            player.unpause()
        elif player.is_playing():
            logger.info("Pausing music playback.")
            player.pause()
        else:
            logger.info("Pause requested but no music is currently playing.")

    def next(self):
        if player.is_playing() or player.is_paused():
            logger.info("Next track.")
            player.next()
        else:
            logger.info("Next requested but no music is currently playing.")

    def previous(self):
        if player.is_playing() or player.is_paused():
            logger.info("Going to previous track.")
            player.previous()
        else:
            logger.info("Previous requested but no music is currently playing.")

    def stop(self):
        if player.is_playing() or player.is_paused():
            logger.info("Stopping music playback.")
            player.stop()
        else:
            logger.info("Stop requested but no music is currently playing.")

    def has_tracks(self) -> bool:
        return player.has_tracks()

    def is_playing(self) -> bool:
        return player.is_playing()

    def is_paused(self) -> bool:
        return player.is_paused()

    def scan_playlist(self, path: str | Path) -> list:
        return player.scan_playlist(Path(path))

    def load_playlist(self, path: str | Path):
        count = player.load_playlist(Path(path))
        if count > 0:
            logger.info("Loaded playlist with %d tracks, starting playback.", count)
            player.play()
        else:
            logger.warning("No playable tracks found in '%s'.", path)

    def set_playlist(self, tracks: list, infos: list):
        count = player.set_playlist(tracks, infos)
        if count > 0:
            logger.info("Set playlist with %d tracks.", count)
        else:
            logger.warning("set_playlist called with empty track list.")

    def add_tracks_batch(self, tracks: list, infos: list) -> bool:
        was_empty = player.add_tracks_batch(tracks, infos)
        logger.info("Batch-added %d tracks.", len(tracks))
        return was_empty

    def current_track_info(self) -> dict:
        return player.current_track_info()

    def get_position(self) -> tuple[float, float]:
        return player.get_position()

    def seek(self, seconds: float):
        player.seek(seconds)

    def get_queue(self) -> tuple[list[dict], int]:
        return player.get_queue()

    def play(self):
        player.play()

    def add_track(self, path: str | Path) -> bool:
        p = Path(path)
        ok = player.add_track(p)
        if ok:
            logger.info("Added track to queue: %s", p.name)
        else:
            logger.warning("Could not add track: %s", path)
        return ok

    def remove_track(self, index: int) -> bool:
        ok = player.remove_track(index)
        if ok:
            logger.info("Removed track at index %d from queue.", index)
        return ok

    def play_track(self, index: int):
        player.play_track(index)

    def toggle_shuffle(self) -> bool:
        state = player.toggle_shuffle()
        logger.info("Shuffle %s.", "enabled" if state else "disabled")
        return state

    def is_shuffle(self) -> bool:
        return player.is_shuffle()


music_service = MusicService()
