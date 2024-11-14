import requests

from transcription_bot.config import AZURE_SERVICE_REGION, AZURE_SUBSCRIPTION_KEY
from transcription_bot.global_logger import logger

_AZURE_SPEECH_ENDPOINT = f"https://{AZURE_SERVICE_REGION}.api.cognitive.microsoft.com"
_AUTH_HEADER = {"Ocp-Apim-Subscription-Key": AZURE_SUBSCRIPTION_KEY}
_API_VERSION_PARAM = {"api-version": "2024-11-15"}
_LOCALE = "en-US"
_TRANSCRIPTION_CONFIG = {
    "profanityFilterMode": "None",
    "punctuationMode": "Automatic",
    "diarization_enabled": True,
    "timeToLive": "PT7d",
    "diarization": {"maxSpeakers": 8},
}


def create_transcription_request_classic(episode_url: str, episode_number: int) -> str:
    """Send a transcription request."""
    transcription_url = f"{_AZURE_SPEECH_ENDPOINT}/speechtotext/v3.2-preview.2/transcriptions"

    payload = {
        "contentUrls": [episode_url],
        "properties": _TRANSCRIPTION_CONFIG,
        "locale": _LOCALE,
        "displayName": f"SGU Episode {episode_number}",
    }

    resp = requests.post(transcription_url, headers=_AUTH_HEADER, json=payload, timeout=5)
    resp.raise_for_status()

    transcription_id = resp.headers["location"].split("/")[-1]

    logger.info(f"Created new transcription with id: {transcription_id}")
    return transcription_id


def create_transcription_request_new(episode_url: str, episode_number: int) -> str:
    """Send a transcription request."""
    transcription_url = f"{_AZURE_SPEECH_ENDPOINT}/speechtotext/transcriptions"

    payload = {
        "contentUrls": [episode_url],
        "properties": _TRANSCRIPTION_CONFIG,
        "locale": _LOCALE,
        "displayName": f"SGU Episode {episode_number}",
    }

    resp = requests.post(transcription_url, headers=_AUTH_HEADER, params=_API_VERSION_PARAM, json=payload, timeout=5)
    resp.raise_for_status()

    transcription_id = resp.headers["location"].split("/")[-1]

    logger.info(f"Created new transcription with id: {transcription_id}")
    return transcription_id
