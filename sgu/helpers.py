from typing import TYPE_CHECKING
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from sgu.caching import file_cache
from sgu.global_http_client import http_client
from sgu.global_logger import logger

if TYPE_CHECKING:
    from bs4 import Tag


def string_is_url(text: str) -> bool:
    """Check if a string is a valid URL."""
    parsed = urlparse(text)
    return all([parsed.scheme, parsed.netloc])


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
        raise ValueError("Unexpected number of description elements extracted, expected 1, got %s", len(results))

    return results[0]


def are_strings_in_string(strings: list[str], string: str) -> bool:
    """Check if all strings are in a given string."""
    return all(s in string for s in strings)


@file_cache
def get_article_title(url: str) -> str:
    """Get the title of an article from its URL."""
    try:
        resp = http_client.get(url)
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching article title at {url} : {e}")
        return "(Tool was unable to retrieve title)"

    if not resp.ok:
        logger.error(f"Error fetching article title: {url}")
        return "(Tool was unable to retrieve title)"

    soup = BeautifulSoup(resp.text, "html.parser")
    title_element = find_single_element(soup, "title", None)
    return title_element.text
