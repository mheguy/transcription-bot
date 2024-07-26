"""When heuristics aren't enough to find the start of a segment, maybe an LLM can help."""

import json
from typing import TYPE_CHECKING

from sgu.caching import file_cache
from sgu.config import LLM_MODEL, OPENAI_API_KEY, OPENAI_ORG, OPENAI_PROJECT
from sgu.custom_logger import logger

if TYPE_CHECKING:
    from sgu.episode_segments import BaseSegment
    from sgu.transcription import DiarizedTranscript

from openai import OpenAI


@file_cache
def ask_llm_for_segment_start(segment: "BaseSegment", transcript: "DiarizedTranscript") -> float | None:
    """Ask an LLM for the start time of a segment."""
    client = OpenAI(organization=OPENAI_ORG, project=OPENAI_PROJECT, api_key=OPENAI_API_KEY)
    system_prompt = (
        "You are a helpful assistant designed to output JSON."
        "The user will provide you with a segment of transcript"
        "from an episode of The Skeptic's Guide to the Universe."
        "The diarization is a best-effort and may contain errors, "
        "indicating the incorrect speaker."
        "The user will also ask you to identify the start time of a segment."
        "Your objective is to provide the time when the transition occurs."
        "The transitions are usually performed by Steve."
        'You must reply with a json object like this: {"start_time": 123.45}'
        "If you cannot identify the transition, provide null as the start time."
    )

    partial_transcript = _get_next_n_minutes_of_transcript(transcript, 30)

    transcript_blob = f"transcript:\n\n````{json.dumps(partial_transcript)}````"
    user_content = f"{segment.llm_prompt}\n\n{transcript_blob}"

    logger.debug(f"Requesting LLM for segment: {segment}")
    response = client.chat.completions.create(
        model=LLM_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
    )

    if not response.choices[0].message.content:
        raise ValueError("LLM did not return a response.")

    response_json: dict[str, float | None] = json.loads(response.choices[0].message.content)
    logger.debug(f"LLM response: {response_json}")

    return response_json.get("start_time")


def _get_next_n_minutes_of_transcript(transcript: "DiarizedTranscript", minutes: int) -> "DiarizedTranscript":
    end_time = transcript[0]["start"] + (minutes * 60)

    return [c for c in transcript if c["end"] < end_time]
