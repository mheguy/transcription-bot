from typing import TYPE_CHECKING, TypeVar
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from transcription_bot.caching import cache_url_title
from transcription_bot.global_http_client import http_client
from transcription_bot.global_logger import logger

if TYPE_CHECKING:
    from bs4 import Tag

    from transcription_bot.episode_segments import BaseSegment, Segments

T = TypeVar("T", bound="BaseSegment")


def are_strings_in_string(strings: list[str], string: str) -> bool:
    """Check if all strings are in a given string."""
    return all(s in string for s in strings)


def find_single_element(soup: "BeautifulSoup | Tag", name: str, class_name: str | None) -> "Tag":
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


@cache_url_title
def get_article_title(url: str) -> str | None:
    """Get the title of an article from its URL."""
    try:
        resp = http_client.get(url)
    except requests.exceptions.RequestException as e:
        logger.exception(f"Error fetching article title at {url} : {e}")
        return None

    if not resp.ok:
        logger.error(f"Error fetching article title: {url}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    title_element = soup.find("title")
    if not title_element:
        return None

    return title_element.text


def get_first_segment_of_type(segments: "Segments", segment_type: type[T]) -> "T | None":
    """Get the first segment of a given type from a list of segments."""
    for segment in segments:
        if isinstance(segment, segment_type):
            return segment

    return None


def string_is_url(text: str) -> bool:
    """Check if a string is a valid URL."""
    parsed = urlparse(text)
    return all([parsed.scheme, parsed.netloc])
