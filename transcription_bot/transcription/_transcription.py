from typing import TYPE_CHECKING

from codetiming import Timer
from openai import OpenAI

from transcription_bot.caching import cache_for_episode
from transcription_bot.config import (
    OPENAI_API_KEY,
    OPENAI_ORG,
    OPENAI_PROJECT,
    TRANSCRIPTION_LANGUAGE,
    TRANSCRIPTION_MODEL,
    TRANSCRIPTION_PROMPT,
)

if TYPE_CHECKING:
    from pathlib import Path

    from openai.types.audio.transcription_verbose import TranscriptionVerbose

    from transcription_bot.parsers.rss_feed import PodcastEpisode

FITEEN_MINUTES = 15 * 60


@cache_for_episode
@Timer("get_transcription_from_openai", "{name} took {:.1f} seconds")
def get_transcription_from_openai(_podcast: "PodcastEpisode", audio_file: "Path") -> "TranscriptionVerbose":
    """Get the transcription from OpenAI."""
    # TODO: Get audio file under the 25MB limit
    # Maybe split? Maybe downsample? TBD.
    client = OpenAI(organization=OPENAI_ORG, project=OPENAI_PROJECT, api_key=OPENAI_API_KEY)

    return client.audio.transcriptions.create(
        file=audio_file,
        model=TRANSCRIPTION_MODEL,
        response_format="verbose_json",
        language=TRANSCRIPTION_LANGUAGE,
        prompt=TRANSCRIPTION_PROMPT,
        timestamp_granularities=["word", "segment"],
        timeout=FITEEN_MINUTES,
    )
