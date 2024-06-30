# region Imports
from __future__ import annotations

import asyncio
import json
import os
import time
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict, cast

import en_core_web_trf
import feedparser
import httpx
import torch
import whisper
from dotenv import load_dotenv
from mutagen.easyid3 import EasyID3
from pyannote.audio.pipelines import SpeakerDiarization
from pyannote.audio.pipelines.utils.hook import ProgressHook
from pyannote.core import Annotation, Segment
from pyannote.core.utils.types import Label, TrackName

if TYPE_CHECKING:
    from httpx import AsyncClient
    from pyannote.core import Annotation
    from spacy.language import Language
    from whisper import Whisper

load_dotenv()
# endregion
# region Config + Constants
RSS_URL = "https://feed.theskepticsguide.org/feed/rss.aspx?feed=sgu"

TRANSCRIPTION_MODEL = "medium.en"
MINIMUM_SPEAKERS = 3  # Always at least the intro voice, Steven, and 1 Rogue.

DATA_FOLDER = Path("data")
EPISODE_FOLDER = DATA_FOLDER / "episodes"
TRANSCRIPTION_FOLDER = DATA_FOLDER / "transcriptions"
DIARIZATION_FOLDER = DATA_FOLDER / "diarization"
DIARIZED_TRANSCRIPT_FOLDER = DATA_FOLDER / "diaried_transcripts"

RSS_FILE = DATA_FOLDER / "rss.xml"
SIX_DAYS = 60 * 60 * 24 * 6
FILE_SIZE_CUTOFF = 100_000

# Debug settings
ENABLE_PODCAST_DOWNLOADING = False
ENABLE_TRANSCRIPTION = False
ENABLE_DIARIZATION = False
ENABLE_DIARIZED_TRANSCRIPT = False


# endregion
# region Custom Types
class PodcastFeedEntryLink(TypedDict):
    """Only the fields we use."""

    length: str
    href: str


class PodcastFeedEntry(TypedDict):
    """Only the fields we use."""

    title: str
    link: str
    links: list[PodcastFeedEntryLink]


class TranscriptionSegment(TypedDict):
    start_time: float
    end_time: float
    text: str


class Transcription(TypedDict):
    text: str
    segments: list[TranscriptionSegment]


class DiarizedTranscriptSegment(TypedDict):
    start_time: str
    end_time: str
    speaker: str | Label
    text: str


class DiarizedTranscript(TypedDict):
    rogues: list[str]
    segments: list[DiarizedTranscriptSegment]


# endregion
# region Helpers
def ensure_directories() -> None:
    """Perform any initial setup."""

    DATA_FOLDER.mkdir(parents=True, exist_ok=True)
    EPISODE_FOLDER.mkdir(parents=True, exist_ok=True)
    TRANSCRIPTION_FOLDER.mkdir(parents=True, exist_ok=True)
    DIARIZATION_FOLDER.mkdir(parents=True, exist_ok=True)


def load_models() -> tuple[Whisper, SpeakerDiarization, Language]:
    print("Loading models..")
    gpu = torch.device("cuda")

    whisper_model = whisper.load_model(TRANSCRIPTION_MODEL, device=gpu)

    pipeline = SpeakerDiarization.from_pretrained(
        "pyannote/speaker-diarization-3.1", use_auth_token=os.getenv("HUGGING_FACE_KEY")
    )
    pipeline.to(gpu)

    nlp = en_core_web_trf.load()
    print("Models loaded.")
    return whisper_model, cast(SpeakerDiarization, pipeline), nlp


def get_podcast_episodes(feed_entries: list[PodcastFeedEntry]) -> list[PodcastEpisode]:
    print("Getting all episodes from feed entries...")
    podcast_episodes: list[PodcastEpisode] = []
    for entry in feed_entries:
        episode_number = int(entry["link"].split("/")[-1])

        if episode_number <= 0:
            print(f"Skipping episode due to number: {entry['title']}")
            continue

        podcast_episodes.append(
            PodcastEpisode(
                episode_number=episode_number,
                download_url=entry["links"][0]["href"],
            )
        )

    return podcast_episodes


async def get_rss_feed_entries(client: AsyncClient) -> list[PodcastFeedEntry]:
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


def merge_transcript_and_diarization(
    transcription: Transcription, diarization: Annotation
) -> list[DiarizedTranscriptSegment]:
    print("Merging transcript and diarization..")
    combined_result: list[DiarizedTranscriptSegment] = []

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
            word_speaker = max(corresponding_speakers, key=lambda s: min(s[1], end_time) - max(s[0], start_time))[2]
        else:
            word_speaker = "Unknown"

        combined_result.append(
            {
                "start_time": format_timestamp(start_time),
                "end_time": format_timestamp(end_time),
                "speaker": word_speaker,
                "text": text,
            }
        )

    print("Merged transcript and diarization.")
    return combined_result


def extract_rogue_names_from_transcription(nlp: Language, transcript: Transcription) -> list[str]:
    intro_text = " ".join(s["text"] for s in transcript["segments"][:100])

    doc = nlp(intro_text)

    names = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]

    valid_names: list[str] = []

    for name in names:
        # Name already in the list or less specific than another name
        if any(valid_name.startswith(name) for valid_name in valid_names):
            continue

        # Name is more specific than a one we have (replace it)
        if any(name.startswith(valid_name) for valid_name in valid_names):
            for index, valid_name in enumerate(valid_names):
                if name.startswith(valid_name):
                    valid_names[index] = name
                    break
            continue

        # Name seems to be unique
        valid_names.append(name)

    return valid_names


# endregion
# region Podcast Episode
@dataclass
class PodcastEpisode:
    episode_number: int
    download_url: str

    @property
    def _audio_file(self) -> Path:
        return EPISODE_FOLDER / f"{self.episode_number:04}.mp3"

    @property
    def transcription_file(self) -> Path:
        return TRANSCRIPTION_FOLDER / f"{self.episode_number:04}.json"

    @property
    def diarization_file(self) -> Path:
        return DIARIZATION_FOLDER / f"{self.episode_number:04}.json"

    @property
    def diarized_transcript_file(self) -> Path:
        return DIARIZED_TRANSCRIPT_FOLDER / f"{self.episode_number:04}.json"

    async def get_audio_file(self, client: AsyncClient) -> Path:
        if self._audio_file.exists():
            return self._audio_file

        await self.download_audio_file(client)
        return self._audio_file

    async def download_audio_file(self, client: AsyncClient) -> None:
        print(f"Downloading episode: {self.episode_number}..")

        resp = await client.get(self.download_url, timeout=3600)
        resp.raise_for_status()
        self._audio_file.write_bytes(resp.content)

        if self._audio_file.stat().st_size < FILE_SIZE_CUTOFF:
            raise RuntimeError(f"Size too small for episode {self.episode_number} (file contains an error message)")

        self.sanitize_mp3_tag(self._audio_file)

        print(f"Downloaded episode: {self.episode_number}.")

    def get_transcription(self, audio_file: Path, whisper_model: Whisper) -> Transcription:
        if self.transcription_file.exists():
            return json.loads(self.transcription_file.read_text("utf-8"))

        return self.create_transcription(audio_file, whisper_model)

    @staticmethod
    def create_transcription(audio_file: Path, whisper_model: Whisper) -> Transcription:
        print(f"Creating transcription for episode: {audio_file}..")

        start = time.time()
        transcription = whisper_model.transcribe(str(audio_file), language="en", verbose=False)
        end = time.time()

        print(f"Created transcription for episode: {audio_file} in {end - start:.2f} seconds.")
        return transcription  # type: ignore

    def get_diarization(self, audio_file: Path, pipeline: SpeakerDiarization, max_speakers: int) -> Annotation:
        if self.diarization_file.exists():
            return json.loads(self.diarization_file.read_text("utf-8"))

        return self.create_diarization(audio_file, pipeline, max_speakers)

    @staticmethod
    def create_diarization(audio_file: Path, pipeline: SpeakerDiarization, max_speakers: int) -> Annotation:
        print(f"Creating diarization for: {audio_file}..")

        with ProgressHook() as hook:
            start = time.time()
            diarization: Annotation = pipeline(
                audio_file,
                hook=hook,
                min_speakers=MINIMUM_SPEAKERS,
                max_speakers=max_speakers,
            )
        end = time.time()

        print(f"Created diarization for: {audio_file} in {end - start:.2f} seconds.")
        return diarization

    @staticmethod
    def sanitize_mp3_tag(mp3_file: Path) -> None:
        id3_tag = EasyID3(mp3_file)

        print(f"Removing ID3 tag from: {mp3_file}")
        id3_tag.delete()
        id3_tag.save()


# endregion


async def main() -> None:
    print("Starting...")
    ensure_directories()
    whisper_model, pipeline, nlp = load_models()

    async with httpx.AsyncClient(follow_redirects=True) as client:
        feed_entries = await get_rss_feed_entries(client)
        episodes = get_podcast_episodes(feed_entries)

        for episode in episodes:
            audio_file = await episode.get_audio_file(client)

            transcription = episode.get_transcription(audio_file, whisper_model)
            episode.transcription_file.write_text(json.dumps(transcription))
            print("Transcription saved.")

            rogues = extract_rogue_names_from_transcription(nlp, transcription)
            max_speakers = len(rogues) + 1  # Add 1 for the intro + Sci or Fict voice

            diarization = episode.get_diarization(audio_file, pipeline, max_speakers)
            episode.diarization_file.write_text(json.dumps(diarization))
            print("Diarization saved.")

            diarized_transcript_segments = merge_transcript_and_diarization(transcription, diarization)

            diarized_transcript = DiarizedTranscript(rogues=rogues, segments=diarized_transcript_segments)
            episode.diarized_transcript_file.write_text(json.dumps(diarized_transcript))

            print("Diarized transcript saved.")

            # Next up, trying to tag the speakers with the rogues' names


if __name__ == "__main__":
    asyncio.run(main())
