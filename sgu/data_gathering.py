import asyncio
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

from mutagen.id3 import ID3

from sgu.caching import file_cache_async
from sgu.config import AUDIO_FOLDER
from sgu.custom_logger import logger
from sgu.downloader import FileDownloader
from sgu.transcription import (
    DiarizedTranscript,
    create_diarization,
    create_transcription,
    load_audio,
    merge_transcript_and_diarization,
)

if TYPE_CHECKING:
    from pathlib import Path

    import requests
    from mutagen.id3._frames import USLT
    from requests import Session

    from sgu.rss_feed import PodcastEpisode


@dataclass
class EpisodeData:
    podcast: "PodcastEpisode"
    transcript: "DiarizedTranscript"
    lyrics: str
    show_notes: bytes


async def gather_data(client: "requests.Session", podcast: "PodcastEpisode") -> EpisodeData:
    print("Getting show notes...")
    audio_file = await get_audio_file(client, podcast)

    async with asyncio.TaskGroup() as tg:
        transcript_task = tg.create_task(get_transcript(audio_file, podcast))
        lyrics_task = tg.create_task(get_lyrics_from_mp3(audio_file.read_bytes()))
        show_notes_task = tg.create_task(get_show_notes(client, podcast.link))

    return EpisodeData(
        podcast=podcast,
        transcript=transcript_task.result(),
        lyrics=lyrics_task.result(),
        show_notes=show_notes_task.result(),
    )


@file_cache_async
async def get_audio_file(client: "Session", podcast: "PodcastEpisode") -> "Path":
    audio_file = AUDIO_FOLDER / f"{podcast.episode_number}.mp3"
    if audio_file.exists():
        audio = audio_file.read_bytes()
    else:
        print("Downloading episode...")
        downloader = FileDownloader(client)
        audio = downloader.download(podcast.download_url)
        audio_file.write_bytes(audio)
    return audio_file


@file_cache_async
async def get_show_notes(client: "Session", url: str) -> bytes:
    resp = client.get(url)
    resp.raise_for_status()

    return resp.content


@file_cache_async
async def get_lyrics_from_mp3(raw_bytes: bytes) -> str:
    audio = ID3(BytesIO(raw_bytes))

    uslt_frame: USLT = audio.getall("USLT::eng")[0]

    result = getattr(uslt_frame, "text", None)

    if result is None:
        raise ValueError("could not find lyrics")

    return result


@file_cache_async
async def get_transcript(audio_file: "Path", podcast: "PodcastEpisode") -> "DiarizedTranscript":
    audio = load_audio(audio_file)

    logger.info("Creating transcript")
    transcription = create_transcription(audio)

    logger.info("Getting diarization")
    diarization = await create_diarization(podcast)

    logger.info("Creating diarized transcript")
    return merge_transcript_and_diarization(transcription, diarization)
