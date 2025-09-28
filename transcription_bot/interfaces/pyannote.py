import json

import pandas as pd
from loguru import logger

from transcription_bot.models.data_models import PodcastRssEntry
from transcription_bot.utils.caching import cache_for_episode
from transcription_bot.utils.config import VOICEPRINT_FILE, config
from transcription_bot.utils.exceptions import DiarizationServiceError
from transcription_bot.utils.global_http_client import http_client

_AUTH_HEADER = {"Authorization": f"Bearer {config.pyannote_token}", "Content-Type": "application/json"}

_HTTP_TIMEOUT = 30


_session = http_client.with_auth_header(_AUTH_HEADER)
del http_client


@cache_for_episode(should_cache=lambda x: x is not None)
def create_diarization(rss_entry: PodcastRssEntry) -> pd.DataFrame | None:
    """Create a diarization DataFrame for the given podcast episode."""
    job_id = _send_diarization_request(rss_entry)

    job_url = f"{config.pyannote_jobs_endpoint}/{job_id}"

    resp = _session.get(job_url, timeout=_HTTP_TIMEOUT)

    resp_object = resp.json()

    match resp_object["status"]:
        case "failed":
            raise DiarizationServiceError(f"Diarization failed. {resp_object}")
        case "succeeded":
            logger.info("Diarization complete.")
        case _:
            logger.info("Diarization incomplete.")
            return None

    return pd.DataFrame(resp_object["output"]["identification"])


@cache_for_episode
def _send_diarization_request(rss_entry: PodcastRssEntry) -> str:
    """Send a diarization request to pyannote."""
    logger.info("Sending diarization request...")

    data = {"url": rss_entry.download_url, "voiceprints": _get_voiceprints()}

    logger.debug(f"Request data: {data}")
    response = _session.post(config.pyannote_identify_endpoint, json=data)
    logger.debug(f"Request sent. Response: {response}")

    return response.json()["jobId"]


def _get_voiceprints() -> list[dict[str, str]]:
    """Retrieve the voiceprint map."""
    voiceprint_map: dict[str, str] = json.loads(VOICEPRINT_FILE.read_text())

    return [{"voiceprint": voiceprint, "label": name} for name, voiceprint in voiceprint_map.items()]
