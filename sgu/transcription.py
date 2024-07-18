import gc
import json
from typing import TYPE_CHECKING, Any, TypedDict, cast

import pandas as pd
import requests
import torch
import whisperx
from codetiming import Timer
from numpy import dtype, floating, ndarray
from whisperx.types import AlignedTranscriptionResult, TranscriptionResult

from sgu.caching import file_cache, file_cache_async
from sgu.config import (
    DIARIZATION_FOLDER,
    PYANNOTE_IDENTIFY_ENDPOINT,
    PYANNOTE_TOKEN,
    TRANSCRIPTION_LANGUAGE,
    TRANSCRIPTION_MODEL,
)
from sgu.custom_logger import logger
from sgu.voiceprints import get_voiceprints
from sgu.webhook_server import WebhookServer

if TYPE_CHECKING:
    from pathlib import Path

    from pandas import DataFrame
    from whisperx.types import AlignedTranscriptionResult, TranscriptionResult

    from sgu.rss_feed import PodcastEpisode

AudioArray = ndarray[Any, dtype[floating[Any]]]


class DiarizedTranscriptSegment(TypedDict):
    start: float
    end: float
    text: str
    speaker: str


DiarizedTranscript = list[DiarizedTranscriptSegment]


def load_audio(audio_file: "Path") -> AudioArray:
    return whisperx.load_audio(str(audio_file))


def create_transcription(audio: AudioArray) -> "AlignedTranscriptionResult":
    device = torch.device("cuda")

    raw_transcription = perform_transcription(audio)

    return perform_alignment(audio, device, raw_transcription)


@file_cache
@Timer("transcription", "{name} took {:.1f} seconds", "{name} starting")
def perform_transcription(audio: AudioArray) -> "TranscriptionResult":
    transcription_model = whisperx.load_model(TRANSCRIPTION_MODEL, "cuda")
    result = transcription_model.transcribe(audio)

    # Unload model
    gc.collect()
    torch.cuda.empty_cache()
    del transcription_model

    return result


@file_cache
@Timer("transcription_alignment", "{name} took {:.1f} seconds", "{name} starting")
def perform_alignment(
    audio: AudioArray, device: torch.device, transcription: "TranscriptionResult"
) -> "AlignedTranscriptionResult":
    alignment_model, metadata = whisperx.load_align_model(language_code=TRANSCRIPTION_LANGUAGE, device=device)
    aligned_transcription = whisperx.align(
        transcription["segments"], alignment_model, metadata, audio, cast(str, device), return_char_alignments=False
    )

    # Unload model
    gc.collect()
    torch.cuda.empty_cache()
    del alignment_model

    return aligned_transcription


@file_cache_async
async def create_diarization(podcast: "PodcastEpisode") -> "DataFrame":
    """Start a web server in a thread, then send a request to pyannote.ai to"""
    diarization_response_file = DIARIZATION_FOLDER / f"{podcast.episode_number}_raw.json"

    if diarization_response_file.exists():
        logger.info("Reading diarization from file")
        dia_response = diarization_response_file.read_bytes()
    else:
        logger.info("Creating diarization")
        webhook_server = WebhookServer()
        server_url = await webhook_server.start_server_thread()

        send_diarization_request(server_url, podcast.download_url)

        dia_response = await webhook_server.get_webhook_payload_async()

        logger.info("Writing diarization response to file")
        diarization_response_file.write_bytes(dia_response)

    response_dict = json.loads(dia_response)
    return pd.DataFrame(response_dict["output"]["identification"])


def send_diarization_request(listener_url: str, audio_file_url: str) -> None:
    webhook_url = f"{listener_url}/webhook"

    headers = {"Authorization": f"Bearer {PYANNOTE_TOKEN}", "Content-Type": "application/json"}
    data = {"webhook": webhook_url, "url": audio_file_url, "voiceprints": get_voiceprints()}

    logger.info("Request data: %s", data)
    response = requests.post(PYANNOTE_IDENTIFY_ENDPOINT, headers=headers, json=data, timeout=10)
    response.raise_for_status()

    logger.info("Request sent. Response: %s", response.content)


def merge_transcript_and_diarization(
    transcription: "AlignedTranscriptionResult", diarization: pd.DataFrame
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
            )
        )

    return segments
