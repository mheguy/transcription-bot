import pickle
from typing import TYPE_CHECKING, cast

from bs4 import BeautifulSoup, ResultSet, Tag

from sgu.custom_types import HeaderData

if TYPE_CHECKING:
    from requests import Session


PODCAST_HEADER_TAG_TYPE = "section"
PODCAST_HEADER_CLASS_NAME = "podcast-head"

PODCAST_MAIN_TAG_TYPE = "main"
PODCAST_MAIN_CLASS_NAME = "podcast-main"


def get_show_notes(client: "Session", url: str) -> BeautifulSoup:
    resp = client.get(url)
    resp.raise_for_status()

    return BeautifulSoup(resp.content, "html.parser")


def extract_element(soup: BeautifulSoup | Tag, name: str, class_name: str) -> Tag:
    results = soup.find_all(name, class_=class_name)

    if len(results) != 1:
        raise ValueError("Unexpected number of description elements extracted, expected 1, got %s", len(results))

    return results[0]


def process_header(header: Tag) -> HeaderData:
    description = extract_element(header, "p", "podcast__description")
    thumbnail_div = extract_element(header, "div", "thumbnail")
    thumbnail = thumbnail_div.findChild("img")
    if not isinstance(thumbnail, Tag):
        raise TypeError("Got an unexpected type in thumbnail")

    return HeaderData(summary=description.text, image=thumbnail.attrs["src"])


def process_post(post_element: Tag) -> list[list["Tag"]]:
    h3_tags = post_element.find_all("h3")

    if any(not isinstance(h3_tag, Tag) for h3_tag in h3_tags):
        raise TypeError("Got an unexpected type in h3 tags")

    h3_tags = cast(ResultSet[Tag], h3_tags)

    raw_segments: list[list[Tag]] = []
    for h3_tag in h3_tags:
        if not h3_tag.text:
            continue

        raw_segment: list[Tag] = [h3_tag]
        for sibling in h3_tag.next_siblings:
            if not isinstance(sibling, Tag):
                continue

            if sibling.name == "h3":
                break

            raw_segment.append(sibling)

        raw_segments.append(raw_segment)

    if len(raw_segments) == 0:
        raise ValueError("Could not find any segments")

    return raw_segments


html: bytes = pickle.load(open("show_notes.pkl", "rb")).content  # noqa: S301, SIM115
soup = BeautifulSoup(html, "html.parser")

header = extract_element(soup, PODCAST_HEADER_TAG_TYPE, PODCAST_HEADER_CLASS_NAME)
header_data = process_header(header)

post = extract_element(soup, PODCAST_MAIN_TAG_TYPE, PODCAST_MAIN_CLASS_NAME)
post_data = process_post(post)

print()
