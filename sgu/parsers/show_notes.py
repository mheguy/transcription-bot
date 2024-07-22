from typing import cast

from bs4 import BeautifulSoup, ResultSet, Tag

from sgu.episode_segments import (
    BaseSegment,
    FromShowNotesSegment,
    Segments,
    SegmentSource,
    UnknownSegment,
    segment_types,
)
from sgu.helpers import find_single_element

PODCAST_HEADER_TAG_TYPE = "section"
PODCAST_HEADER_CLASS_NAME = "podcast-head"
PODCAST_MAIN_TAG_TYPE = "main"
PODCAST_MAIN_CLASS_NAME = "podcast-main"


def get_episode_image_url(show_notes: bytes) -> str:
    """Extract the episode image URL from the show notes."""
    soup = BeautifulSoup(show_notes, "html.parser")

    header = find_single_element(soup, PODCAST_HEADER_TAG_TYPE, PODCAST_HEADER_CLASS_NAME)

    thumbnail_div = find_single_element(header, "div", "thumbnail")
    thumbnail = thumbnail_div.findChild("img")
    if not isinstance(thumbnail, Tag):
        raise TypeError("Got an unexpected type in thumbnail")

    return thumbnail.attrs["src"]


def parse_show_notes(show_notes: bytes) -> Segments:
    """Parse the show notes HTML and return a list of segments."""
    soup = BeautifulSoup(show_notes, "html.parser")

    post = find_single_element(soup, PODCAST_MAIN_TAG_TYPE, PODCAST_MAIN_CLASS_NAME)
    segment_data = _extract_segment_data(post)

    return list(filter(None, [_parse_show_notes_segment_data(segment_data) for segment_data in segment_data]))


def _parse_show_notes_segment_data(segment_data: list["Tag"]) -> "BaseSegment|None":
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

    return UnknownSegment.create(text=text, source=SegmentSource.NOTES)


def _extract_segment_data(post_element: Tag) -> list[list["Tag"]]:
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
