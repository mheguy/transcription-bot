import asyncio
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

from mutagen.id3 import ID3

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
    from mutagen.id3._frames import USLT
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


async def gather_data(client: "requests.Session", podcast: "PodcastEpisode") -> EpisodeData:
    """Gather data about a podcast episode."""
    logger.info("Getting show data...")
    audio_file = await get_audio_file(client, podcast)

    async with asyncio.TaskGroup() as tg:
        transcript_task = tg.create_task(get_transcript(podcast, audio_file))
        lyrics_task = tg.create_task(_get_lyrics_from_mp3(audio_file.read_bytes()))
        show_notes_task = tg.create_task(_get_show_notes(client, podcast.episode_url))

    return EpisodeData(
        podcast=podcast,
        transcript=transcript_task.result(),
        lyrics=lyrics_task.result(),
        show_notes=show_notes_task.result(),
    )


async def get_audio_file(client: "Session", podcast: "PodcastEpisode") -> "Path":
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


async def _get_show_notes(client: "Session", url: str) -> bytes:
    resp = client.get(url)
    resp.raise_for_status()

    return resp.content


async def _get_lyrics_from_mp3(raw_bytes: bytes) -> str:
    audio = ID3(BytesIO(raw_bytes))

    uslt_frame: USLT = audio.getall("USLT::eng")[0]

    result = getattr(uslt_frame, "text", None)

    if result is None:
        raise ValueError("could not find lyrics")

    return result
