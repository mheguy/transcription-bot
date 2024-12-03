from datetime import date
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup, Tag

from transcription_bot.caching import cache_url_title
from transcription_bot.global_http_client import http_client
from transcription_bot.global_logger import logger

_BASELINE_EPISODE_NUMBER = 1000
_BASELINE_EPISODE_DATE = date(2024, 9, 7)
_MISALIGNED_EPISODES = {
    442: 2014,
    390: 2013,
    338: 2012,
    234: 2009,
    233: 2010,
    232: 2010,
    181: 2009,
    129: 2008,
    128: 2008,
    77: 2007,
    76: 2007,
    25: 2006,
    24: 2006,
}


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


@cache_url_title
def get_article_title(url: str) -> str | None:
    """Get the title of an article from its URL."""
    try:
        resp = http_client.get(url, timeout=2)
    except requests.exceptions.RequestException as e:
        logger.exception(f"Error fetching article title at {url} : {e}")
        return None

    if not resp.ok:
        logger.error(f"Error fetching article title: {url} : {resp.status_code}")
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
