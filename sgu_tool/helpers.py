import os
from collections.abc import Iterator
from datetime import timedelta
from typing import TYPE_CHECKING, cast

import feedparser
import spacy
import torch
import whisper
from pyannote.audio.pipelines import SpeakerDiarization
from pyannote.core import Annotation, Segment
from pyannote.core.utils.types import Label, TrackName

from sgu_tool.config import (
    DIARIZATION_FOLDER,
    DIARIZED_TRANSCRIPT_FOLDER,
    OUTPUT_FOLDER,
    RSS_URL,
    TRANSCRIPTION_FOLDER,
    TRANSCRIPTION_MODEL,
)
from sgu_tool.episode import PodcastEpisode
from sgu_tool.main import (
    TEMP_FOLDER,
    Whisper,
)

if TYPE_CHECKING:
    from httpx import AsyncClient
    from pyannote.core import Annotation
    from spacy.language import Language
    from whisper import Whisper

    from sgu_tool.custom_types import DiarizedTranscriptSegment, PodcastFeedEntry, Transcription


def ensure_directories() -> None:
    """Perform any initial setup."""

    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    TRANSCRIPTION_FOLDER.mkdir(parents=True, exist_ok=True)
    DIARIZATION_FOLDER.mkdir(parents=True, exist_ok=True)
    DIARIZED_TRANSCRIPT_FOLDER.mkdir(parents=True, exist_ok=True)
    TEMP_FOLDER.mkdir(parents=True, exist_ok=True)


def load_models() -> tuple["Whisper", SpeakerDiarization, "Language"]:
    print("Loading models..")
    gpu = torch.device("cuda")

    print("Loading whisper...")
    whisper_model = whisper.load_model(TRANSCRIPTION_MODEL, device=gpu)

    print("Loading pyannote...")
    pipeline = SpeakerDiarization.from_pretrained(
        "pyannote/speaker-diarization-3.1", use_auth_token=os.getenv("HUGGING_FACE_KEY")
    )
    pipeline.to(gpu)

    print("Loading spacy...")
    nlp = spacy.load("en_core_web_trf")

    print("Models loaded.")
    return whisper_model, cast(SpeakerDiarization, pipeline), nlp


def get_podcast_episodes(feed_entries: list["PodcastFeedEntry"]) -> list[PodcastEpisode]:
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


async def get_rss_feed_entries(client: "AsyncClient") -> list["PodcastFeedEntry"]:
    print("Getting RSS feed entries...")
    response = await client.get(RSS_URL, timeout=10)
    response.raise_for_status()
    rss_content = response.text

    return feedparser.parse(rss_content)["entries"]


def format_timestamp(seconds: float) -> str:
    return str(timedelta(seconds=int(seconds)))


def merge_transcript_and_diarization(
    transcription: "Transcription", diarization: "Annotation"
) -> list["DiarizedTranscriptSegment"]:
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


def extract_rogue_names_from_transcription(nlp: "Language", transcript: "Transcription") -> list[str]:
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
