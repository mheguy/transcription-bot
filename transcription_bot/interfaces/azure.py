import json
from typing import Any
from urllib.parse import urlencode

from loguru import logger

from transcription_bot.models.data_models import PodcastRssEntry
from transcription_bot.models.simple_models import RawTranscript, RecognizedPhrase
from transcription_bot.utils.caching import cache_for_episode
from transcription_bot.utils.config import config
from transcription_bot.utils.global_http_client import http_client
from transcription_bot.utils.helpers import download_file

_HTTP_TIMEOUT = 30
_API_VERSION_PARAM = {"api-version": "2024-11-15"}
_LOCALE = "en-US"
_TRANSCRIPTION_CONFIG = {
    "profanityFilterMode": "None",
    "punctuationMode": "Automatic",
    "timeToLiveHours": 720,
    "diarization": {"enabled": True, "maxSpeakers": 8},
    "wordLevelTimestampsEnabled": True,
}
_AUTH_HEADER = {"Ocp-Apim-Subscription-Key": config.azure_subscription_key}
_API_BASE_URL = f"https://{config.azure_service_region}.api.cognitive.microsoft.com"
_TRANSCRIPTIONS_ENDPOINT = f"{_API_BASE_URL}/speechtotext/transcriptions"


# One tick is 100 nanoseconds
_TICKS_PER_SECONDS = 10_000_000

_session = http_client.with_auth_header(_AUTH_HEADER)
del http_client


@cache_for_episode
def send_transcription_request(rss_entry: PodcastRssEntry) -> str:
    """Send a transcription request."""
    payload = {
        "contentUrls": [rss_entry.download_url],
        "properties": _TRANSCRIPTION_CONFIG,
        "locale": _LOCALE,
        "displayName": f"SGU Episode {rss_entry.episode_number}",
        "customProperties": {"episode_number": str(rss_entry.episode_number)},
    }

    resp = _session.post(
        f"{_TRANSCRIPTIONS_ENDPOINT}:submit", params=_API_VERSION_PARAM, json=payload, timeout=_HTTP_TIMEOUT
    )

    transcription_url: str = resp.json()["self"]

    logger.info(f"Created new transcription with url: {transcription_url}")
    return transcription_url


def get_all_transcriptions() -> list[dict[str, Any]]:
    """Get all transcriptions from Azure."""

    # The inner function allows us to omit the URL parameter from the outer function.
    def recursive_transcription_getter(url: str | None = None) -> list[dict[str, Any]]:
        if not url:
            url = f"{_TRANSCRIPTIONS_ENDPOINT}?{urlencode(_API_VERSION_PARAM)}"

        resp = _session.get(url, timeout=_HTTP_TIMEOUT).json()
        transcriptions: list[Any] = resp["values"]

        if "@nextLink" in resp:
            transcriptions.extend(recursive_transcription_getter(resp["@nextLink"]))

        return transcriptions

    return recursive_transcription_getter()


def get_transcription_results(files_url: str) -> RawTranscript:
    """Get the transcription results."""
    resp = _session.get(files_url, timeout=_HTTP_TIMEOUT)

    content = resp.json()

    content_url: str = ""
    for val in content["values"]:
        if val["kind"] == "Transcription":
            content_url = val["links"]["contentUrl"]

    if not content_url:
        raise ValueError("Unable to locate transcription in results: %s", content["values"])

    return _convert_raw_transcription(json.loads(download_file(content_url, _session)))


def _convert_raw_transcription(raw_transcription: dict[str, Any]) -> RawTranscript:
    """Convert raw transcription to a list of transcript segments."""
    recognized_phrases: list[RecognizedPhrase] = raw_transcription["recognizedPhrases"]

    transcription: RawTranscript = []

    for recognized_phrase in recognized_phrases:
        best_guess = recognized_phrase["nBest"]

        if not best_guess:
            logger.error(f"Found a segment without a best guess: {recognized_phrase}")
            continue

        start = recognized_phrase["offsetInTicks"] / _TICKS_PER_SECONDS
        end = start + (recognized_phrase["durationInTicks"] / _TICKS_PER_SECONDS)

        transcription.append(
            {
                "start": start,
                "end": end,
                "text": _perform_low_level_text_corrections(best_guess[0]["display"]),
            }
        )

    return transcription


def _perform_low_level_text_corrections(text: str) -> str:
    """Perform any low level text corrections."""
    return text.replace("Kara", "Cara")
