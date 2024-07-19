from typing import TYPE_CHECKING

from bs4 import Tag

if TYPE_CHECKING:
    from bs4 import BeautifulSoup


def get_url_from_tag(item: "Tag") -> str:
    url = ""
    if a_tag_with_href := item.select_one('div > a[href]:not([href=""])'):
        href = a_tag_with_href["href"]
        url = href if isinstance(href, str) else href[0]

    return url


def extract_element(soup: "BeautifulSoup | Tag", name: str, class_name: str) -> Tag:
    results = soup.find_all(name, class_=class_name)

    if len(results) != 1:
        raise ValueError("Unexpected number of description elements extracted, expected 1, got %s", len(results))

    return results[0]


def extract_image_url(header: "Tag") -> str:
    thumbnail_div = extract_element(header, "div", "thumbnail")
    thumbnail = thumbnail_div.findChild("img")
    if not isinstance(thumbnail, Tag):
        raise TypeError("Got an unexpected type in thumbnail")

    return thumbnail.attrs["src"]
