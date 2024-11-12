from typing import TYPE_CHECKING, TypedDict

import numpy as np
import pandas as pd

from transcription_bot.caching import cache_for_episode
from transcription_bot.global_logger import logger
from transcription_bot.transcription._diarization import create_diarization
from transcription_bot.transcription._transcription import get_transcription_from_openai

if TYPE_CHECKING:
    from pathlib import Path

    from openai.types.audio.transcription_verbose import TranscriptionVerbose

    from transcription_bot.parsers.rss_feed import PodcastEpisode

DiarizedTranscript = list["DiarizedTranscriptChunk"]


class DiarizedTranscriptChunk(TypedDict):
    """A chunk of a diarized transcript.

    Attributes:
        start (float): The start time of the chunk.
        end (float): The end time of the chunk.
        text (str): The text content of the chunk.
        speaker (str): The speaker associated with the chunk.
    """

    start: float
    end: float
    text: str
    speaker: str


@cache_for_episode
def get_diarized_transcript(podcast: "PodcastEpisode", audio_file: "Path") -> "DiarizedTranscript":
    """Create a transcript with the audio and podcast information."""
    logger.debug("get_transcript")

    openai_transcription = get_transcription_from_openai(podcast, audio_file)

    raw_diarization = create_diarization(podcast)
    diarization = pd.DataFrame(raw_diarization["output"]["identification"])

    return merge_transcript_and_diarization(openai_transcription, diarization)


def merge_transcript_and_diarization(
    transcription: "TranscriptionVerbose",
    diarization: pd.DataFrame,
) -> DiarizedTranscript:
    logger.debug("Merging transcript and diarization...")

    if transcription.segments is None:
        raise TypeError("transcription.segments is None")

    diarized_transcript: DiarizedTranscript = []

    for seg in transcription.segments:
        if not seg.text:
            continue

        # assign speaker to segment (if any)
        diarization["intersection"] = np.minimum(diarization["end"], seg.end) - np.maximum(
            diarization["start"], seg.start
        )

        # Filter speakers during this segment of diarization
        segment_speakers = diarization[diarization["intersection"] > 0]

        if len(segment_speakers) > 0:
            # Select the speaker with that was detected most in this timeframe
            segment_speaker = (
                segment_speakers.groupby("speaker")["intersection"].sum().sort_values(ascending=False).index[0]
            )

            if not isinstance(segment_speaker, str):
                raise TypeError(f"Unexpected speaker type: {type(segment_speaker)}")
        else:
            segment_speaker = "UNKNOWN"

        diarized_transcript.append(
            DiarizedTranscriptChunk(start=seg.start, end=seg.end, text=seg.text, speaker=segment_speaker)
        )

    adjust_transcript_for_voiceover(diarized_transcript)

    return diarized_transcript


def adjust_transcript_for_voiceover(complete_transcript: "DiarizedTranscript") -> None:
    """Adjust the transcript for voiceover."""
    voiceover = complete_transcript[0]["speaker"]

    if "SPEAKER_" not in voiceover:
        return

    for chunk in complete_transcript:
        if chunk["speaker"] == voiceover:
            chunk["speaker"] = "Voice-over"
