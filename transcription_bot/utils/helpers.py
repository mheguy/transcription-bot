import sys
from typing import TYPE_CHECKING, TypeVar
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup, Tag
from loguru import logger
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import ConnectTimeout, ReadTimeout, RequestException

from transcription_bot.utils.caching import cache_for_url
from transcription_bot.utils.config import UNPROCESSABLE_EPISODES, config
from transcription_bot.utils.global_http_client import http_client

if TYPE_CHECKING:
    from transcription_bot.models.episode_segments import BaseSegment, GenericSegmentList

T = TypeVar("T", bound="BaseSegment")
_HTTP_TIMEOUT = 15


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


@cache_for_url
def get_article_title(url: str) -> str | None:
    """Get the title of an article from its URL."""
    url = url.replace("http://", "https://")

    try:
        resp = http_client.get(url, timeout=_HTTP_TIMEOUT)
    except (ValueError, ConnectTimeout, ReadTimeout, RequestsConnectionError) as e:
        logger.warning(f"{type(e).__name__} error for {url}")
        return None
    except RequestException as e:
        logger.exception(f"{type(e).__name__} error fetching article title at {url} : {e}")
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


def download_file(url: str, client: requests.Session) -> bytes:
    """Download a file from the given URL."""
    response = client.get(url)
    response.raise_for_status()

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


@cache_for_url
def resolve_url_redirects(url: str) -> str:
    """Resolve URL redirects."""
    try:
        response = http_client.head(url, allow_redirects=True, timeout=_HTTP_TIMEOUT)
        response.raise_for_status()
    except RequestException as e:
        logger.exception(f"Error resolving redirects for {url}: {e}")
        return url

    return response.url


def init_logging() -> None:
    """Initialize loguru logger."""
    logger.remove()

    if config.local_mode:
        logger.add(
            sys.stdout,
            format="{time:HH:mm:ss} <level>{level: <8}</level> [transcript-bot] {message}",
            level=config.log_level,
            colorize=True,
        )
    else:
        logger.add(
            sys.stdout,
            format="[transcript-bot] - {level: <8} - {message}",
            level=config.log_level,
            colorize=False,
        )
