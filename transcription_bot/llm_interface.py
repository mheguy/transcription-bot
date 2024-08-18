"""When heuristics aren't enough to find the start of a segment, maybe an LLM can help."""

import json
from typing import TYPE_CHECKING

from transcription_bot.caching import cache_for_episode, cache_llm
from transcription_bot.config import LLM_MODEL, OPENAI_API_KEY, OPENAI_ORG, OPENAI_PROJECT
from transcription_bot.global_logger import logger

if TYPE_CHECKING:
    from transcription_bot.episode_segments import BaseSegment
    from transcription_bot.parsers.rss_feed import PodcastEpisode
    from transcription_bot.transcription import DiarizedTranscript

from openai import OpenAI


@cache_llm
def ask_llm_for_segment_start(
    _podcast_episode: "PodcastEpisode", segment: "BaseSegment", transcript: "DiarizedTranscript"
) -> float | None:
    """Ask an LLM for the start time of a segment."""
    client = OpenAI(organization=OPENAI_ORG, project=OPENAI_PROJECT, api_key=OPENAI_API_KEY)
    system_prompt = (
        "You are a helpful assistant designed to output JSON."
        "The user will provide you with a section of transcript"
        "from an episode of The Skeptic's Guide to the Universe."
        "The diarization is a best-effort and may contain errors, "
        "indicating the incorrect speaker."
        "The user will also ask you to identify the start time of a segment."
        "Your objective is to provide the time when the transition occurs."
        "The transitions are usually performed by Steve."
        'You must reply with a json object like this: {"start_time": 123.45}'
        "If you cannot identify the transition, provide null as the start time."
        "You shoould provide the start of the transition."
        "Ex. If the transcript is:"
        "'All right, well, let's go on with our interview. We are joined now by Forrest Valkai.'"
        "You should return the timestamp for the beginning of 'All right, well, let's go on with our interview.'"
    )

    transcript_blob = f"transcript:\n\n````{json.dumps(transcript)}````"
    user_prompt = f"{segment.llm_prompt}\n\n{transcript_blob}"

    logger.debug(f"Requesting LLM find start of segment: {segment}")
    response = client.chat.completions.create(
        model=LLM_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    if not response.choices[0].message.content:
        raise ValueError("LLM did not return a response.")

    response_json: dict[str, float | None] = json.loads(response.choices[0].message.content)
    logger.debug(f"LLM response: {response_json}")

    return response_json.get("start_time")


@cache_for_episode
def ask_llm_for_image_caption(_podcast_episode: "PodcastEpisode", image_url: str) -> str:
    """Ask an LLM to write an image caption."""
    user_prompt = "Please write a 10-15 word caption for this image."

    client = OpenAI(organization=OPENAI_ORG, project=OPENAI_PROJECT, api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }
        ],
    )

    if not response.choices[0].message.content:
        raise ValueError("LLM did not return a response.")

    image_caption = response.choices[0].message.content
    logger.debug(f"LLM response: {image_caption}")

    return image_caption
