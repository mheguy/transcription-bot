from io import BytesIO

from mutagen.id3 import ID3
from mutagen.id3._frames import TXXX, USLT
from requests import Session

from transcription_bot.caching import cache_for_episode
from transcription_bot.data_models import EpisodeData, PodcastRssEntry
from transcription_bot.global_logger import logger
from transcription_bot.helpers import download_file


def gather_metadata(rss_entry: PodcastRssEntry, client: Session) -> EpisodeData:
    """Gather metadata about a podcast episode."""
    logger.info("Getting show data...")
    mp3 = get_audio_file(rss_entry, client)

    lyrics = get_lyrics_from_mp3(rss_entry, mp3)
    show_notes = get_show_notes(rss_entry, client)

    return EpisodeData(podcast=rss_entry, lyrics=lyrics, show_notes=show_notes)


def get_lyrics_from_mp3(_rss_entry: PodcastRssEntry, raw_bytes: bytes) -> str:
    """Get the lyrics from an MP3 file."""
    audio = ID3(BytesIO(raw_bytes))

    frame: TXXX | USLT
    if (tag := audio.getall("TXXX:lyrics-eng")) or (tag := audio.getall("USLT::eng")):
        frame = tag[0]
    else:
        raise ValueError("Could not find lyrics tag")

    result: str | list[str] | None = getattr(frame, "text", None)

    if result is None:
        raise ValueError("Could not find lyrics in tag")

    if isinstance(result, str):
        return result

    if len(result) > 1:
        raise ValueError("Multiple lyrics found in tag")

    return result[0]


@cache_for_episode
def get_audio_file(rss_entry: PodcastRssEntry, client: Session) -> bytes:
    """Retrieve the audio file for a podcast episode."""
    logger.info("Downloading episode...")
    return download_file(rss_entry.download_url, client)


@cache_for_episode
def get_show_notes(rss_entry: PodcastRssEntry, client: Session) -> bytes:
    """Get the show notes from the website."""
    resp = client.get(rss_entry.episode_url)
    resp.raise_for_status()

    return resp.content
