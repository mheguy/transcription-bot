import gc
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypedDict, cast

import pandas as pd
import requests
import torch
import whisperx
from codetiming import Timer
from numpy import dtype, floating, ndarray
from whisperx.types import AlignedTranscriptionResult, TranscriptionResult

from transcription_bot.config import (
    DIARIZATION_FOLDER,
    DIARIZED_TRANSCRIPTION_FOLDER,
    PYANNOTE_IDENTIFY_ENDPOINT,
    PYANNOTE_TOKEN,
    TRANSCRIPTION_LANGUAGE,
    TRANSCRIPTION_MODEL,
    TRANSCRIPTION_PROMPT,
    VOICEPRINT_FILE,
)
from transcription_bot.global_logger import logger
from transcription_bot.parsers.rss_feed import PodcastEpisode
from transcription_bot.webhook_server import WebhookServer

if TYPE_CHECKING:
    from pathlib import Path

    from pandas import DataFrame
    from whisperx.types import AlignedTranscriptionResult, TranscriptionResult

    from transcription_bot.parsers.rss_feed import PodcastEpisode

AudioArray = ndarray[Any, dtype[floating[Any]]]


class DiarizedTranscriptSegment(TypedDict):
    """A segment of a diarized transcript.

    Attributes:
        start (float): The start time of the segment.
        end (float): The end time of the segment.
        text (str): The text content of the segment.
        speaker (str): The speaker associated with the segment.
    """

    start: float
    end: float
    text: str
    speaker: str


DiarizedTranscript = list[DiarizedTranscriptSegment]


async def get_transcript(audio_file: "Path", podcast: "PodcastEpisode") -> "DiarizedTranscript":
    """Create a transcript with the audio and podcast information."""
    diarized_transcript_file = DIARIZED_TRANSCRIPTION_FOLDER / f"{podcast.episode_number}.json"

    if diarized_transcript_file.exists():
        logger.info("Reading diarized transcript from file")
        return json.loads(diarized_transcript_file.read_text())

    logger.info("Creating transcript")

    audio = _load_audio(audio_file)

    device = torch.device("cuda")
    raw_transcription = _perform_transcription(audio)
    transcription = _perform_alignment(audio, device, raw_transcription)

    logger.info("Getting diarization")
    diarization = await _create_diarization(podcast)

    logger.info("Creating diarized transcript")
    diarized_transcript = _merge_transcript_and_diarization(transcription, diarization)

    logger.info("Writing diarized transcript to file")
    diarized_transcript_file.write_text(json.dumps(diarized_transcript))

    return diarized_transcript


def _load_audio(audio_file: "Path") -> AudioArray:
    return whisperx.load_audio(str(audio_file))


async def _create_diarization(podcast: "PodcastEpisode") -> "DataFrame":
    diarization_response_file = DIARIZATION_FOLDER / f"{podcast.episode_number}.json"

    if diarization_response_file.exists():
        logger.info("Reading diarization from file")
        dia_response = diarization_response_file.read_bytes()
    else:
        logger.info("Creating diarization")
        webhook_server = WebhookServer()
        server_url = await webhook_server.start_server_thread()

        _send_diarization_request(server_url, podcast.download_url)

        dia_response = await webhook_server.get_webhook_payload_async()

        logger.info("Writing diarization response to file")
        diarization_response_file.write_bytes(dia_response)

    response_dict = json.loads(dia_response)
    return pd.DataFrame(response_dict["output"]["identification"])


def _send_diarization_request(listener_url: str, audio_file_url: str) -> None:
    webhook_url = f"{listener_url}/webhook"

    headers = {"Authorization": f"Bearer {PYANNOTE_TOKEN}", "Content-Type": "application/json"}
    data = {"webhook": webhook_url, "url": audio_file_url, "voiceprints": _get_voiceprints()}

    logger.info(f"Request data: {data}")
    response = requests.post(PYANNOTE_IDENTIFY_ENDPOINT, headers=headers, json=data, timeout=10)
    response.raise_for_status()

    logger.info(f"Request sent. Response: {response.content}")


def _merge_transcript_and_diarization(
    transcription: "AlignedTranscriptionResult",
    diarization: pd.DataFrame,
) -> DiarizedTranscript:
    raw_diarized_transcript: dict[str, list[dict[str, Any]]] = whisperx.assign_word_speakers(diarization, transcription)

    segments: DiarizedTranscript = []
    for segment in raw_diarized_transcript["segments"]:
        segments.append(
            DiarizedTranscriptSegment(
                start=segment["start"],
                end=segment["end"],
                text=segment["text"],
                speaker=segment.get("speaker", "UNKNOWN"),
            ),
        )

    return segments


@Timer("transcription", "{name} took {:.1f} seconds", "{name} starting")
def _perform_transcription(audio: AudioArray) -> "TranscriptionResult":
    transcription_model = whisperx.load_model(
        TRANSCRIPTION_MODEL,
        "cuda",
        asr_options={"initial_prompt": TRANSCRIPTION_PROMPT},
    )
    result = transcription_model.transcribe(audio)

    # Unload model
    gc.collect()
    torch.cuda.empty_cache()
    del transcription_model

    return result


@Timer("transcription_alignment", "{name} took {:.1f} seconds", "{name} starting")
def _perform_alignment(
    audio: AudioArray,
    device: torch.device,
    transcription: "TranscriptionResult",
) -> "AlignedTranscriptionResult":
    alignment_model, metadata = whisperx.load_align_model(language_code=TRANSCRIPTION_LANGUAGE, device=device)
    aligned_transcription = whisperx.align(
        transcription["segments"],
        alignment_model,
        metadata,
        audio,
        cast(str, device),
        return_char_alignments=False,
    )

    # Unload model
    gc.collect()
    torch.cuda.empty_cache()
    del alignment_model

    return aligned_transcription


def _get_voiceprints() -> list[dict[str, str]]:
    voiceprint_map: dict[str, str] = json.loads(VOICEPRINT_FILE.read_text())

    return [{"voiceprint": voiceprint, "label": name} for name, voiceprint in voiceprint_map.items()]
