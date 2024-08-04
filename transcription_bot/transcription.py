import gc
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypedDict, cast

import pandas as pd
import requests
from codetiming import Timer
from numpy import dtype, floating, ndarray

from transcription_bot.caching import cache_for_episode
from transcription_bot.config import (
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

    import torch
    from pandas import DataFrame
    from whisperx.types import AlignedTranscriptionResult, TranscriptionResult

    from transcription_bot.parsers.rss_feed import PodcastEpisode

AudioArray = ndarray[Any, dtype[floating[Any]]]


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


DiarizedTranscript = list[DiarizedTranscriptChunk]


def get_transcript(podcast: "PodcastEpisode", audio_file: "Path") -> "DiarizedTranscript":
    """Create a transcript with the audio and podcast information."""
    diarized_transcript_file = DIARIZED_TRANSCRIPTION_FOLDER / f"{podcast.episode_number}.json"

    if diarized_transcript_file.exists():
        logger.info("Using cache for: get_transcript")
        return json.loads(diarized_transcript_file.read_text())

    logger.info("Creating transcript")
    import torch

    audio = _load_audio(audio_file)

    device = torch.device("cuda")
    raw_transcription = _perform_transcription(podcast, audio)
    transcription = _perform_alignment(audio, device, raw_transcription)

    logger.info("Getting diarization")
    diarization = _create_diarization(podcast)

    logger.info("Creating diarized transcript")
    diarized_transcript = _merge_transcript_and_diarization(transcription, diarization)

    logger.info("Writing diarized transcript to file")
    diarized_transcript_file.write_text(json.dumps(diarized_transcript))

    return diarized_transcript


def _load_audio(audio_file: "Path") -> AudioArray:
    import whisperx

    return whisperx.load_audio(str(audio_file))


@cache_for_episode
def _create_diarization(podcast: "PodcastEpisode") -> "DataFrame":
    logger.info("Creating diarization")
    webhook_server = WebhookServer()
    server_url = webhook_server.start_server_thread()

    _send_diarization_request(server_url, podcast.download_url)

    dia_response = webhook_server.get_webhook_payload()

    response_dict = json.loads(dia_response)
    return pd.DataFrame(response_dict["output"]["identification"])


def _send_diarization_request(listener_url: str, audio_file_url: str) -> None:
    webhook_url = f"{listener_url}/webhook"

    headers = {"Authorization": f"Bearer {PYANNOTE_TOKEN}", "Content-Type": "application/json"}
    data = {"webhook": webhook_url, "url": audio_file_url, "voiceprints": _get_voiceprints()}

    logger.info(f"Request data: {data}")
    response = requests.post(PYANNOTE_IDENTIFY_ENDPOINT, headers=headers, json=data, timeout=10)
    logger.info(f"Request sent. Response: {response}")
    response.raise_for_status()


def _merge_transcript_and_diarization(
    transcription: "AlignedTranscriptionResult",
    diarization: pd.DataFrame,
) -> DiarizedTranscript:
    import whisperx

    raw_diarized_transcript: dict[str, list[dict[str, Any]]] = whisperx.assign_word_speakers(diarization, transcription)

    chunks: DiarizedTranscript = []
    for chunk in raw_diarized_transcript["segments"]:
        chunks.append(
            DiarizedTranscriptChunk(
                start=chunk["start"],
                end=chunk["end"],
                text=chunk["text"],
                speaker=chunk.get("speaker", "UNKNOWN"),
            ),
        )

    return chunks


@Timer("transcription", "{name} took {:.1f} seconds", "{name} starting")
@cache_for_episode
def _perform_transcription(_podcast: "PodcastEpisode", audio: AudioArray) -> "TranscriptionResult":
    import torch
    import whisperx

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
    device: "torch.device",
    transcription: "TranscriptionResult",
) -> "AlignedTranscriptionResult":
    import torch
    import whisperx

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
