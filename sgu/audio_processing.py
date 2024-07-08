import gc
import os
from typing import TYPE_CHECKING, Any, cast

import torch
import whisperx
from codetiming import Timer
from numpy import dtype, floating, ndarray
from whisperx.types import AlignedTranscriptionResult

from sgu import config

if TYPE_CHECKING:
    from pathlib import Path

    from pandas import DataFrame
    from whisperx.types import AlignedTranscriptionResult, TranscriptionResult

AudioArray = ndarray[Any, dtype[floating[Any]]]

TIMER_TEXT = "{name} took {:.1f} seconds"
TIMER_INITIAL_TEXT = "{name} starting"


@Timer("full audio processing", TIMER_TEXT, TIMER_INITIAL_TEXT)
def perform_audio_processing(audio_file: "Path", speaker_count: int) -> "AlignedTranscriptionResult":
    device = torch.device("cuda")

    audio: AudioArray = whisperx.load_audio(str(audio_file))

    transcription = perform_transcription(audio)

    # NOTE: This mutates the transcription object rather than creating a copy
    aligned_transcription = perform_alignment(audio, device, transcription)

    diarized_segments = perform_diarization(audio, device, speaker_count)

    return whisperx.assign_word_speakers(diarized_segments, aligned_transcription)


@Timer("transcription", TIMER_TEXT, TIMER_INITIAL_TEXT)
def perform_transcription(audio: AudioArray) -> "TranscriptionResult":
    transcription_model = whisperx.load_model(config.TRANSCRIPTION_MODEL, "cuda")
    result = transcription_model.transcribe(audio)

    # Unload model
    gc.collect()
    torch.cuda.empty_cache()
    del transcription_model

    return result


@Timer("transcription alignment", TIMER_TEXT, TIMER_INITIAL_TEXT)
def perform_alignment(
    audio: AudioArray, device: torch.device, transcription: "TranscriptionResult"
) -> "AlignedTranscriptionResult":
    alignment_model, metadata = whisperx.load_align_model(language_code=config.TRANSCRIPTION_LANGUAGE, device=device)
    aligned_transcription = whisperx.align(
        transcription["segments"], alignment_model, metadata, audio, cast(str, device), return_char_alignments=False
    )

    # Unload model
    gc.collect()
    torch.cuda.empty_cache()
    del alignment_model

    return aligned_transcription


@Timer("diarization", TIMER_TEXT, TIMER_INITIAL_TEXT)
def perform_diarization(audio: AudioArray, device: torch.device, speaker_count: int) -> "DataFrame":
    hf_token = os.environ["HUGGING_FACE_KEY"]
    diarization_model = whisperx.DiarizationPipeline(use_auth_token=hf_token, device=device)

    return diarization_model(audio, min_speakers=speaker_count, max_speakers=speaker_count)
