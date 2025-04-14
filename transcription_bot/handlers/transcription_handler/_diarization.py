import json
import time
from typing import Any

import pandas as pd
from loguru import logger

from transcription_bot.models.data_models import PodcastRssEntry
from transcription_bot.utils.caching import cache_for_episode
from transcription_bot.utils.config import VOICEPRINT_FILE, config
from transcription_bot.utils.global_http_client import http_client

_AUTH_HEADER = {"Authorization": f"Bearer {config.pyannote_token}", "Content-Type": "application/json"}

_HTTP_TIMEOUT = 30


_session = http_client.with_auth_header(_AUTH_HEADER)
del http_client


@cache_for_episode
def create_diarization(rss_entry: PodcastRssEntry) -> pd.DataFrame:
    job_id = send_diarization_request(rss_entry)
    job_url = f"{config.pyannote_jobs_endpoint}/{job_id}"
    raw_diarization = wait_for_diarization_completion(job_url)

    return pd.DataFrame(raw_diarization["output"]["identification"])


@cache_for_episode
def send_diarization_request(rss_entry: PodcastRssEntry) -> str:
    """Send a diarization request to pyannote."""
    logger.info("Sending diarization request...")

    data = {"url": rss_entry.download_url, "voiceprints": get_voiceprints()}

    logger.debug(f"Request data: {data}")
    response = _session.post(config.pyannote_identify_endpoint, json=data)
    logger.debug(f"Request sent. Response: {response}")

    return response.json()["jobId"]


def get_voiceprints() -> list[dict[str, str]]:
    """Retrieve the voiceprint map."""
    voiceprint_map: dict[str, str] = json.loads(VOICEPRINT_FILE.read_text())

    return [{"voiceprint": voiceprint, "label": name} for name, voiceprint in voiceprint_map.items()]


def wait_for_diarization_completion(diarization_url: str) -> Any:
    logger.info("Waiting for diarization to complete...")

    while True:
        resp = _session.get(diarization_url, timeout=_HTTP_TIMEOUT)

        resp_object = resp.json()
        status = resp_object["status"]

        if status == "succeeded":
            logger.info("Diarization complete.")
            break

        if status == "failed":
            raise RuntimeError(f"Diarization failed. {resp_object}")

        logger.info(f"Waiting 1 minute, status: {status}")
        time.sleep(60)

    return resp_object
