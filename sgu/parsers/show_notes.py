from dataclasses import dataclass
from typing import cast

from bs4 import BeautifulSoup, ResultSet, Tag

from sgu.segments import BaseSegment, UnknownSegment, segment_mapping


def parse_show_notes_segment_data(segment_data: list["Tag"]) -> "BaseSegment|None":
    text = segment_data[0].text
    lower_text = text.lower()

    for segment_class in segment_mapping["from_notes"]:
        if segment_class.match_string(lower_text):
            return segment_class.from_show_notes(segment_data)

    for segment_class in segment_mapping["from_summary"]:
        if segment_class.match_string(lower_text):
            return None

    return UnknownSegment(text=text, source="notes")


def get_url_from_tag(item: "Tag") -> str:
    url = ""
    if a_tag_with_href := item.select_one('div > a[href]:not([href=""])'):
        href = a_tag_with_href["href"]
        url = href if isinstance(href, str) else href[0]

    return url


RawSegmentData = list[list["Tag"]]


@dataclass
class ShowNotesData:
    image_url: str
    segment_data: "RawSegmentData"


def extract_element(soup: BeautifulSoup | Tag, name: str, class_name: str) -> Tag:
    results = soup.find_all(name, class_=class_name)

    if len(results) != 1:
        raise ValueError("Unexpected number of description elements extracted, expected 1, got %s", len(results))

    return results[0]


PODCAST_HEADER_TAG_TYPE = "section"
PODCAST_HEADER_CLASS_NAME = "podcast-head"
PODCAST_MAIN_TAG_TYPE = "main"
PODCAST_MAIN_CLASS_NAME = "podcast-main"


def extract_image_url(header: Tag) -> str:
    thumbnail_div = extract_element(header, "div", "thumbnail")
    thumbnail = thumbnail_div.findChild("img")
    if not isinstance(thumbnail, Tag):
        raise TypeError("Got an unexpected type in thumbnail")

    return thumbnail.attrs["src"]


def extract_segment_data(post_element: Tag) -> RawSegmentData:
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


def parse_show_notes(raw_show_notes: bytes) -> ShowNotesData:
    soup = BeautifulSoup(raw_show_notes, "html.parser")

    header = extract_element(soup, PODCAST_HEADER_TAG_TYPE, PODCAST_HEADER_CLASS_NAME)
    image_url = extract_image_url(header)

    post = extract_element(soup, PODCAST_MAIN_TAG_TYPE, PODCAST_MAIN_CLASS_NAME)
    segment_data = extract_segment_data(post)

    return ShowNotesData(image_url=image_url, segment_data=segment_data)
