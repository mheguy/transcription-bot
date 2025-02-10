import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeVar
from urllib.parse import urlparse

import cronitor
import sentry_sdk
from bs4 import BeautifulSoup, Tag
from loguru import logger
from requests import Session
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import ConnectTimeout, ReadTimeout, RequestException
from sentry_sdk.integrations.loguru import LoggingLevels, LoguruIntegration
from tls_client.exceptions import TLSClientExeption

from transcription_bot.utils.caching import cache_for_str_arg
from transcription_bot.utils.config import UNPROCESSABLE_EPISODES, ConfigProto
from transcription_bot.utils.global_http_client import get_with_evasion, http_client

if TYPE_CHECKING:
    from transcription_bot.models.episode_segments import BaseSegment, GenericSegmentList

T = TypeVar("T", bound="BaseSegment")


def are_strings_in_string(strings: list[str], string: str) -> bool:
    """Check if all strings are in a given string."""
    return all(s in string for s in strings)


def find_single_element(soup: "BeautifulSoup | Tag", name: str, class_name: str | None) -> Tag:
    """Extract a single HTML element from a BeautifulSoup object or Tag.

    Args:
        soup: The BeautifulSoup object or Tag to search in.
        name: The name of the HTML element to extract. Ex. "span"
        class_name: The CSS class name of the HTML element to extract. Ex. "description"

    Returns:
        Tag: The extracted HTML element.

    Raises:
        ValueError: If the number of extracted elements is not equal to 1.
    """
    results = soup.find_all(name, class_=class_name)

    if len(results) != 1:
        raise ValueError(f"Unexpected number of description elements extracted, expected 1, got {len(results)}")

    return results[0]


@cache_for_str_arg
def get_article_title(url: str) -> str | None:
    """Get the title of an article from its URL."""
    url = url.replace("http://", "https://")
    resp = None

    try:
        resp = http_client.get(url, raise_for_status=False)
    except (ValueError, ConnectTimeout, ReadTimeout, RequestsConnectionError) as e:
        logger.warning(f"{type(e).__name__} error for {url}")
    except RequestException as e:
        logger.exception(f"{type(e).__name__} error fetching article title at {url} : {e}")

    if resp is None or not resp.ok:
        try:
            resp = get_with_evasion(url)
        except TLSClientExeption:
            logger.warning(f"Got TLS exception for url {url}")
            return None

    if not resp.ok:
        logger.warning(f"Error fetching article title: {url} : {resp.status_code}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    title_element = soup.find("title")
    if not title_element:
        return None

    return title_element.text


def string_is_url(text: str) -> bool:
    """Check if a string is a valid URL."""
    parsed = urlparse(text)
    return all([parsed.scheme, parsed.netloc])


def download_file(url: str, client: Session) -> bytes:
    """Download a file from the given URL."""
    response = client.get(url)

    return response.content


def filter_bad_episodes(episode_numbers: set[int]) -> list[int]:
    """Removes episodes that cannot be processed and issues a warning."""
    bad_episode_numbers = episode_numbers.intersection(UNPROCESSABLE_EPISODES)
    if bad_episode_numbers:
        logger.warning(f"Unable to process episodes: {bad_episode_numbers}. See UNPROCESSABLE_EPISODES.")

    good_episodes = episode_numbers.difference(UNPROCESSABLE_EPISODES)

    return sorted(good_episodes)


def get_first_segment_of_type(segments: "GenericSegmentList", segment_type: type[T]) -> "T | None":
    """Get the first segment of a given type from a list of segments."""
    for segment in segments:
        if isinstance(segment, segment_type):
            return segment

    return None


@cache_for_str_arg
def resolve_url_redirects(url: str) -> str:
    """Resolve URL redirects."""
    try:
        response = http_client.head(url, allow_redirects=True)
    except RequestException as e:
        logger.exception(f"Error resolving redirects for {url}: {e}")
        return url

    return response.url


def run_main_safely(func: Callable[..., None], *args: Any, **kwargs: Any) -> None:
    """Run a function safely, logging any exceptions and providing a graceful exit."""
    try:
        with sentry_sdk.start_transaction(op="task", name=func.__module__):
            func(*args, **kwargs)
    except Exception:
        logger.exception("Exiting due to exception.")
        raise
    else:
        logger.info("Exiting without exception.")
    finally:
        print("Waiting 3s for any messages to flush..")
        time.sleep(3)  # allow monitors to flush


def setup_tracing(config: ConfigProto) -> None:
    """Set up tracing."""
    if not config.local_mode:
        sentry_loguru = LoguruIntegration(
            level=LoggingLevels.DEBUG.value,
            event_level=LoggingLevels.ERROR.value,
        )

        sentry_sdk.init(
            dsn=config.sentry_dsn,
            environment="production",
            traces_sample_rate=1.0,
            profiles_sample_rate=1.0,
            integrations=[sentry_loguru],
        )
        cronitor.api_key = config.cronitor_api_key
