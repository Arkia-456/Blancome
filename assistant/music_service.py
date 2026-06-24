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

    def load_playlist(self, path: str | Path):
        count = player.load_playlist(Path(path))
        if count > 0:
            logger.info("Loaded playlist with %d tracks, starting playback.", count)
            player.play()
        else:
            logger.warning("No playable tracks found in '%s'.", path)

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

    def play_track(self, index: int):
        player.play_track(index)


music_service = MusicService()
