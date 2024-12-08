import concurrent.futures

import numpy as np
import pandas as pd

from transcription_bot.handlers.transcription_handler._diarization import create_diarization
from transcription_bot.handlers.transcription_handler._transcription import RawTranscript, create_transcription
from transcription_bot.models.data_models import DiarizedTranscript, DiarizedTranscriptChunk, PodcastRssEntry
from transcription_bot.utils.global_logger import logger


def get_diarized_transcript(podcast: PodcastRssEntry) -> DiarizedTranscript:
    """Create a transcript with the audio and podcast information."""
    logger.info("Getting diarized transcript...")

    with concurrent.futures.ThreadPoolExecutor() as executor:
        transcription_future = executor.submit(create_transcription, podcast)
        diarization_future = executor.submit(create_diarization, podcast)

        transcription = transcription_future.result()
        diarization = diarization_future.result()

    return merge_transcript_and_diarization(transcription, diarization)


def merge_transcript_and_diarization(transcription: RawTranscript, diarization: "pd.DataFrame") -> DiarizedTranscript:
    logger.info("Merging transcript and diarization...")
    diarized_transcript: DiarizedTranscript = []

    for seg in transcription:
        if not seg["text"]:
            continue

        # Find active speakers during the segment
        diarization["intersection"] = np.minimum(diarization["end"], seg["end"]) - np.maximum(
            diarization["start"], seg["start"]
        )
        segment_speakers = diarization[diarization["intersection"] > 0]

        if len(segment_speakers) > 0:
            # Select the most active speaker
            segment_speaker = (
                segment_speakers.groupby("speaker")["intersection"].sum().sort_values(ascending=False).index[0]  # pyright: ignore[reportCallIssue]
            )

            if not isinstance(segment_speaker, str):
                raise TypeError(f"Unexpected speaker type: {type(segment_speaker)}")
        else:
            segment_speaker = "UNKNOWN"

        diarized_transcript.append(
            DiarizedTranscriptChunk(start=seg["start"], end=seg["end"], text=seg["text"], speaker=segment_speaker)
        )

    adjust_transcript_for_voiceover(diarized_transcript)

    return diarized_transcript


def adjust_transcript_for_voiceover(complete_transcript: DiarizedTranscript) -> None:
    """Adjust the transcript for voiceover."""
    voiceover = complete_transcript[0]["speaker"]

    if "SPEAKER_" not in voiceover:
        return

    for chunk in complete_transcript:
        if chunk["speaker"] == voiceover:
            chunk["speaker"] = "Voice-over"