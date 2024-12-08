import json

import pandas as pd
import requests
from loguru import logger

from transcription_bot.models.data_models import PodcastRssEntry
from transcription_bot.utils.caching import cache_for_episode
from transcription_bot.utils.config import VOICEPRINT_FILE, config
from transcription_bot.utils.webhook_server import WebhookServer


@cache_for_episode
def create_diarization(podcast: PodcastRssEntry) -> pd.DataFrame:
    logger.info("Creating diarization...")
    webhook_server = WebhookServer()
    server_url = webhook_server.start_server_thread()

    try:
        send_diarization_request(server_url, podcast.download_url)
    except Exception:
        logger.exception("Failed to send diarization request")
        webhook_server.stop_server_thread()
        raise

    response_content = webhook_server.get_webhook_payload()

    try:
        raw_diarization = json.loads(response_content)
    except (TypeError, OverflowError, json.JSONDecodeError, UnicodeDecodeError):
        logger.exception(f"Failed to decode to JSON: {response_content}")
        raise

    return pd.DataFrame(raw_diarization["output"]["identification"])


def get_voiceprints() -> list[dict[str, str]]:
    voiceprint_map: dict[str, str] = json.loads(VOICEPRINT_FILE.read_text())

    return [{"voiceprint": voiceprint, "label": name} for name, voiceprint in voiceprint_map.items()]


def send_diarization_request(listener_url: str, audio_file_url: str) -> None:
    logger.info("Sending diarization request...")
    webhook_url = f"{listener_url}/webhook"

    headers = {"Authorization": f"Bearer {config.pyannote_token}", "Content-Type": "application/json"}
    data = {"webhook": webhook_url, "url": audio_file_url, "voiceprints": get_voiceprints()}

    logger.debug(f"Request data: {data}")
    response = requests.post(config.pyannote_identify_endpoint, headers=headers, json=data, timeout=10)
    logger.debug(f"Request sent. Response: {response}")
    response.raise_for_status()
