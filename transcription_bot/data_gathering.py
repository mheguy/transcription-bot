from dataclasses import dataclass
from io import BytesIO
from typing import TYPE_CHECKING

from mutagen.id3 import ID3

from transcription_bot.caching import cache_for_episode
from transcription_bot.global_logger import logger
from transcription_bot.helpers import download_file
from transcription_bot.transcription import Transcript, get_transcript

if TYPE_CHECKING:
    import requests
    from mutagen.id3._frames import TXXX, USLT
    from requests import Session

    from transcription_bot.parsers.rss_feed import PodcastEpisode


@dataclass
class EpisodeData:
    """Detailed data about a podcast episode.

    Attributes:
        podcast: The basic information about the episode.
        transcript: The diarized transcript of the episode.
        lyrics: The lyrics that were embedded in the MP3 file.
        show_notes: The show notes of the episode from the website.
    """

    podcast: "PodcastEpisode"
    transcript: "Transcript"
    lyrics: str
    show_notes: bytes


@cache_for_episode
def gather_data(podcast: "PodcastEpisode", client: "requests.Session") -> EpisodeData:
    """Gather data about a podcast episode."""
    logger.info("Getting show data...")
    mp3 = get_audio_file(podcast, client)

    transcript = get_transcript(podcast)
    lyrics = get_lyrics_from_mp3(podcast, mp3)
    show_notes = _get_show_notes(podcast, client)

    return EpisodeData(podcast=podcast, transcript=transcript, lyrics=lyrics, show_notes=show_notes)


@cache_for_episode
def get_audio_file(podcast: "PodcastEpisode", client: "Session") -> bytes:
    """Retrieve the audio file for a podcast episode."""
    logger.info("Downloading episode...")
    return download_file(podcast.download_url, client)


@cache_for_episode
def get_lyrics_from_mp3(_podcast: "PodcastEpisode", raw_bytes: bytes) -> str:
    """Get the lyrics from an MP3 file."""
    audio = ID3(BytesIO(raw_bytes))

    frame: TXXX | USLT
    if (tag := audio.getall("TXXX:lyrics-eng")) or (tag := audio.getall("USLT::eng")):
        frame = tag[0]
    else:
        raise ValueError("Could not find lyrics tag")

    result = getattr(frame, "text", None)

    if result is None:
        raise ValueError("Could not find lyrics in tag")

    return result


@cache_for_episode
def _get_show_notes(podcast: "PodcastEpisode", client: "Session") -> bytes:
    resp = client.get(podcast.episode_url)
    resp.raise_for_status()

    return resp.content
