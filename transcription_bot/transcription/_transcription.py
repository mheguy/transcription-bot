import json
import time
from typing import TYPE_CHECKING, Any, TypedDict

import requests

from transcription_bot.caching import cache_for_episode
from transcription_bot.config import config
from transcription_bot.global_logger import logger
from transcription_bot.helpers import download_file

if TYPE_CHECKING:
    from transcription_bot.parsers.rss_feed import PodcastRssEntry

# At the time of writing, API version 2024-11-15 is not yet available
# When it becomes available, switch api version param and remove the version from the endpoint
_API_VERSION_PARAM = {}
# _API_VERSION_PARAM = {"api-version": "2024-11-15"}
_TRANSCRIPTIONS_ENDPOINT = (
    f"https://{config.azure_service_region}.api.cognitive.microsoft.com/speechtotext/v3.2-preview.2/transcriptions"
)

_AUTH_HEADER = {"Ocp-Apim-Subscription-Key": config.azure_subscription_key}
_LOCALE = "en-US"
_TRANSCRIPTION_CONFIG = {
    "profanityFilterMode": "None",
    "punctuationMode": "Automatic",
    "diarizationEnabled": True,
    "timeToLive": "P1M",
    "diarization": {"speakers": {"minCount": 4, "maxCount": 8}},
}
_HTTP_TIMEOUT = 30

# One tick is 100 nanoseconds
_TICKS_PER_SECONDS = 10_000_000

Transcription = list["TranscriptSegment"]

session = requests.Session()
session.headers.update(_AUTH_HEADER)


class TranscriptSegment(TypedDict):
    start: float
    end: float
    text: str


class PhraseInfo(TypedDict):
    display: str


class RecognizedPhrase(TypedDict):
    offsetInTicks: float
    durationInTicks: float
    nBest: list[PhraseInfo]


def create_transcription(podcast: "PodcastRssEntry") -> Transcription:
    """Send a transcription request."""
    transcription_id = send_transcription_request(podcast, _TRANSCRIPTIONS_ENDPOINT)
    transcription_url = f"{_TRANSCRIPTIONS_ENDPOINT}/{transcription_id}"
    files_url = wait_for_transcription_completion(transcription_url)
    return get_transcription_results(files_url)


@cache_for_episode
def send_transcription_request(podcast: "PodcastRssEntry", transcriptions_endpoint: str) -> str:
    payload = {
        "contentUrls": [podcast.download_url],
        "properties": _TRANSCRIPTION_CONFIG,
        "locale": _LOCALE,
        "displayName": f"SGU Episode {podcast.episode_number}",
    }

    resp = session.post(transcriptions_endpoint, params=_API_VERSION_PARAM, json=payload, timeout=_HTTP_TIMEOUT)
    resp.raise_for_status()

    transcription_id = resp.headers["location"].split("/")[-1]

    logger.info(f"Created new transcription with id: {transcription_id}")
    return transcription_id


def wait_for_transcription_completion(transcription_url: str) -> str:
    logger.info("Waiting for transcription to complete...")

    while True:
        resp = session.get(transcription_url, params=_API_VERSION_PARAM, timeout=_HTTP_TIMEOUT)
        resp.raise_for_status()

        resp_object = resp.json()
        status = resp_object["status"]

        if status == "Succeeded":
            logger.info("Transcription complete.")
            break

        if status == "Failed":
            logger.error(f"Transcription failed. {resp_object}")
            raise RuntimeError(f"Transcription failed. {resp_object}")

        logger.info(f"Waiting 1 minute, status: {status}")
        time.sleep(60)

    return resp_object["links"]["files"]


def get_transcription_results(files_url: str) -> Transcription:
    resp = session.get(files_url, params=_API_VERSION_PARAM, timeout=_HTTP_TIMEOUT)
    resp.raise_for_status()

    content = resp.json()

    content_url: str = ""
    for val in content["values"]:
        if val["kind"] == "Transcription":
            content_url = val["links"]["contentUrl"]

    if not content_url:
        raise ValueError("Unable to locate transcription in results: %s", content["values"])

    return convert_raw_transcription(json.loads(download_file(content_url, session)))


def convert_raw_transcription(raw_transcription: dict[str, Any]) -> Transcription:
    recognized_phrases: list[RecognizedPhrase] = raw_transcription["recognizedPhrases"]

    transcription: Transcription = []

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
                "text": best_guess[0]["display"],
            }
        )

    return transcription
