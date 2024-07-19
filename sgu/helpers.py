from typing import TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    from bs4 import BeautifulSoup, Tag


def string_is_url(text: str) -> bool:
    parsed = urlparse(text)
    return all([parsed.scheme, parsed.netloc])


def extract_element(soup: "BeautifulSoup | Tag", name: str, class_name: str) -> "Tag":
    results = soup.find_all(name, class_=class_name)

    if len(results) != 1:
        raise ValueError("Unexpected number of description elements extracted, expected 1, got %s", len(results))

    return results[0]
