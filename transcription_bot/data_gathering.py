from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

from mutagen.id3 import ID3

from transcription_bot.caching import cache_for_episode
from transcription_bot.config import AUDIO_FOLDER
from transcription_bot.downloader import FileDownloader
from transcription_bot.global_logger import logger
from transcription_bot.transcription import (
    DiarizedTranscript,
    get_transcript,
)

if TYPE_CHECKING:
    from pathlib import Path

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
    transcript: "DiarizedTranscript"
    lyrics: str
    show_notes: bytes


@cache_for_episode
def gather_data(podcast: "PodcastEpisode", client: "requests.Session") -> EpisodeData:
    """Gather data about a podcast episode."""
    logger.info("Getting show data...")
    audio_file = get_audio_file(client, podcast)

    transcript = get_transcript(podcast, audio_file)
    lyrics = get_lyrics_from_mp3(podcast, audio_file.read_bytes())
    show_notes = _get_show_notes(podcast, client)

    return EpisodeData(
        podcast=podcast,
        transcript=transcript,
        lyrics=lyrics,
        show_notes=show_notes,
    )


def get_audio_file(client: "Session", podcast: "PodcastEpisode") -> "Path":
    """Retrieve the audio file for a podcast episode."""
    audio_file = AUDIO_FOLDER / f"{podcast.episode_number}.mp3"
    if audio_file.exists():
        audio = audio_file.read_bytes()
    else:
        logger.info("Downloading episode...")
        downloader = FileDownloader(client)
        audio = downloader.download(podcast.download_url)
        audio_file.write_bytes(audio)
    return audio_file


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
