import json
from typing import TYPE_CHECKING

import requests

from transcription_bot.caching import cache_for_episode
from transcription_bot.config import PYANNOTE_IDENTIFY_ENDPOINT, PYANNOTE_TOKEN, VOICEPRINT_FILE
from transcription_bot.global_logger import logger
from transcription_bot.webhook_server import WebhookServer

if TYPE_CHECKING:
    from transcription_bot.parsers.rss_feed import PodcastEpisode

RawDiarization = dict[str, dict[str, list[dict[str, str | float]]]]


@cache_for_episode
def create_diarization(podcast: "PodcastEpisode") -> RawDiarization:
    logger.debug("_create_diarization")
    webhook_server = WebhookServer()
    server_url = webhook_server.start_server_thread()

    send_diarization_request(server_url, podcast.download_url)

    response_content = webhook_server.get_webhook_payload()

    try:
        return json.loads(response_content)
    except (TypeError, OverflowError, json.JSONDecodeError, UnicodeDecodeError):
        logger.error(f"Failed to decode to JSON: {response_content}")
        raise


def get_voiceprints() -> list[dict[str, str]]:
    voiceprint_map: dict[str, str] = json.loads(VOICEPRINT_FILE.read_text())

    return [{"voiceprint": voiceprint, "label": name} for name, voiceprint in voiceprint_map.items()]


def send_diarization_request(listener_url: str, audio_file_url: str) -> None:
    logger.debug("_send_diarization_request")
    webhook_url = f"{listener_url}/webhook"

    headers = {"Authorization": f"Bearer {PYANNOTE_TOKEN}", "Content-Type": "application/json"}
    data = {"webhook": webhook_url, "url": audio_file_url, "voiceprints": get_voiceprints()}

    logger.info(f"Request data: {data}")
    response = requests.post(PYANNOTE_IDENTIFY_ENDPOINT, headers=headers, json=data, timeout=10)
    logger.info(f"Request sent. Response: {response}")
    response.raise_for_status()
