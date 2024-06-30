import time
from collections.abc import Iterator
from datetime import timedelta
from typing import TYPE_CHECKING, cast

import feedparser
from mutagen.easyid3 import EasyID3
from pyannote.core import Annotation, Segment
from pyannote.core.utils.types import Label, TrackName

from sgu_sof_tool.config import DATA_FOLDER, DIARIZATION_FOLDER, EPISODE_FOLDER, RSS_URL, TRANSCRIPTION_FOLDER
from sgu_sof_tool.podcast_episode import RSS_FILE, SIX_DAYS, Episode

if TYPE_CHECKING:
    from pathlib import Path

    from httpx import AsyncClient

    from sgu_sof_tool.custom_types import PodcastFeedEntry, Transcription


def ensure_directories() -> None:
    """Perform any initial setup."""

    DATA_FOLDER.mkdir(parents=True, exist_ok=True)
    EPISODE_FOLDER.mkdir(parents=True, exist_ok=True)
    TRANSCRIPTION_FOLDER.mkdir(parents=True, exist_ok=True)
    DIARIZATION_FOLDER.mkdir(parents=True, exist_ok=True)


def get_podcast_episodes(feed_entries: list["PodcastFeedEntry"]) -> list[Episode]:
    print("Getting all episodes from feed entries...")
    podcast_episodes: list[Episode] = []
    for entry in feed_entries:
        episode_number = int(entry["link"].split("/")[-1])

        if episode_number <= 0:
            print(f"Skipping episode due to number: {entry['title']}")
            continue

        podcast_episodes.append(
            Episode(
                episode_number=episode_number,
                download_url=entry["links"][0]["href"],
                expected_file_size=int(entry["links"][0]["length"]),
            )
        )

    return podcast_episodes


async def get_rss_feed_entries(client: "AsyncClient") -> list["PodcastFeedEntry"]:
    print("Getting RSS feed entries...")
    if RSS_FILE.exists() and time.time() - SIX_DAYS < RSS_FILE.stat().st_mtime:
        rss_content = RSS_FILE.read_text()
    else:
        response = await client.get(RSS_URL, timeout=10)
        response.raise_for_status()
        rss_content = response.text
        RSS_FILE.parent.mkdir(parents=True, exist_ok=True)
        RSS_FILE.write_text(rss_content)

    return feedparser.parse(rss_content)["entries"]


def format_timestamp(seconds: float) -> str:
    return str(timedelta(seconds=int(seconds)))


def merge_transcript_and_diarization(transcription: "Transcription", diarization: "Annotation"):
    combined_result = []

    # Convert diarization result into a list of (start, end, speaker)
    speaker_segments: list[tuple[float, float, Label]] = []
    for speech_turn, _, speaker in cast(
        Iterator[tuple[Segment, TrackName, Label]], diarization.itertracks(yield_label=True)
    ):
        speaker_segments.append((speech_turn.start, speech_turn.end, speaker))

    # For each word segment, determine its speaker
    words = cast(list[dict[str, str | float]], transcription["segments"])
    for word in words:
        start_time = cast(float, word["start"])
        end_time = cast(float, word["end"])
        text = cast(str, word["text"])

        corresponding_speakers = [s for s in speaker_segments if s[0] <= start_time < s[1] or s[0] < end_time <= s[1]]

        if corresponding_speakers:
            # If multiple speakers intersect, choose the one with the longest overlap
            speaker = max(corresponding_speakers, key=lambda s: min(s[1], end_time) - max(s[0], start_time))[2]
        else:
            speaker = "Unknown"

        combined_result.append(
            {
                "start_time": format_timestamp(start_time),
                "end_time": format_timestamp(end_time),
                "speaker": speaker,
                "text": text,
            }
        )


def sanitize_mp3_tag(mp3_file: "Path") -> None:
    id3_tag = EasyID3(mp3_file)

    print(f"Removing ID3 tag from: {mp3_file}")
    id3_tag.delete()
    id3_tag.save()
