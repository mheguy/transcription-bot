from typing import cast

from bs4 import BeautifulSoup, ResultSet, Tag

from sgu.parsers.soup_helpers import extract_element, extract_image_url
from sgu.segment_types import (
    BaseSegment,
    FromShowNotesSegment,
    Segments,
    UnknownSegment,
    segment_types,
)

PODCAST_HEADER_TAG_TYPE = "section"
PODCAST_HEADER_CLASS_NAME = "podcast-head"
PODCAST_MAIN_TAG_TYPE = "main"
PODCAST_MAIN_CLASS_NAME = "podcast-main"


def get_episode_image(raw_show_notes: bytes) -> str:
    soup = BeautifulSoup(raw_show_notes, "html.parser")

    header = extract_element(soup, PODCAST_HEADER_TAG_TYPE, PODCAST_HEADER_CLASS_NAME)
    return extract_image_url(header)


def parse_show_notes(show_notes: bytes) -> Segments:
    soup = BeautifulSoup(show_notes, "html.parser")

    post = extract_element(soup, PODCAST_MAIN_TAG_TYPE, PODCAST_MAIN_CLASS_NAME)
    segment_data = extract_segment_data(post)

    return list(filter(None, [parse_show_notes_segment_data(segment_data) for segment_data in segment_data]))


def parse_show_notes_segment_data(segment_data: list["Tag"]) -> "BaseSegment|None":
    text = segment_data[0].text
    lower_text = text.lower()

    found_match = False
    for segment_class in segment_types:
        if segment_class.match_string(lower_text):
            found_match = True
            if issubclass(segment_class, FromShowNotesSegment):
                return segment_class.from_show_notes(segment_data)

    if found_match:
        return None

    return UnknownSegment(text=text, source="notes")


def extract_segment_data(post_element: Tag) -> list[list["Tag"]]:
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
