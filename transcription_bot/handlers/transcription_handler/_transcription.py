import time

from loguru import logger

from transcription_bot.interfaces.azure import get_transcription_results, send_transcription_request
from transcription_bot.models.data_models import PodcastRssEntry
from transcription_bot.models.simple_models import RawTranscript
from transcription_bot.utils.caching import cache_for_episode
from transcription_bot.utils.config import config
from transcription_bot.utils.global_http_client import http_client

_AUTH_HEADER = {"Ocp-Apim-Subscription-Key": config.azure_subscription_key}

_HTTP_TIMEOUT = 30


_session = http_client.with_auth_header(_AUTH_HEADER)


@cache_for_episode
def create_transcription(rss_entry: PodcastRssEntry) -> RawTranscript:
    """Send a transcription request."""
    transcription_url = send_transcription_request(rss_entry)
    files_url = wait_for_transcription_completion(transcription_url)
    return get_transcription_results(files_url)


def wait_for_transcription_completion(transcription_url: str) -> str:
    logger.info("Waiting for transcription to complete...")

    while True:
        resp = _session.get(transcription_url, timeout=_HTTP_TIMEOUT)

        resp_object = resp.json()
        status = resp_object["status"]

        if status == "Succeeded":
            logger.info("Transcription complete.")
            break

        if status == "Failed":
            raise RuntimeError(f"Transcription failed. {resp_object}")

        logger.info(f"Waiting 1 minute for transcription. Current status: {status}")
        time.sleep(60)

    return resp_object["links"]["files"]
