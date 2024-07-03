import itertools
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, TypedDict, cast

from bs4 import Tag

if TYPE_CHECKING:
    from sgu.rss_feed import PodcastFeedEntry
    from sgu.show_notes import ShowNotesData


def create_segments(feed_data: "PodcastFeedEntry", notes_data: "ShowNotesData") -> "list[BaseSegment]":
    print("Creating segments...")

    notes_segments = [parse_show_notes_segment_data(seg_data) for seg_data in notes_data.segment_data]

    feed_segments = [create_segment_from_summary_text(line.strip()) for line in feed_data.summary.split(";")]

    segments = [seg for seg in itertools.chain(notes_segments, feed_segments) if seg is not None]
    print(f"Created {len(segments)} segments.")

    return segments


class BaseSegment(ABC):
    @staticmethod
    @abstractmethod
    def match_string(text: str) -> bool:
        raise NotImplementedError


@dataclass
class UnknownSegment(BaseSegment):
    text: str

    @staticmethod
    def match_string(text: str) -> bool:
        del text
        return True


# region From Summary Text
def create_segment_from_summary_text(text: str) -> "BaseSegment|None":
    for segment_class in segment_types["from_summary"]:
        if segment_class.match_string(text):
            return segment_class.from_summary_text(text)

    for segment_class in segment_types["from_notes"]:
        if segment_class.match_string(text):
            return None

    return UnknownSegment(text)


class FromSummaryTextSegment(BaseSegment, ABC):
    @staticmethod
    @abstractmethod
    def from_summary_text(text: str) -> "FromSummaryTextSegment":
        raise NotImplementedError


@dataclass
class QuickieSegment(FromSummaryTextSegment):
    text: str

    @staticmethod
    def match_string(text: str) -> bool:
        return text.startswith("Quickie with ")

    @staticmethod
    def from_summary_text(text: str) -> "FromSummaryTextSegment":
        return QuickieSegment(text)


@dataclass
class EmailSegment(FromSummaryTextSegment):
    items: list[str]

    @staticmethod
    def match_string(text: str) -> bool:
        return text.startswith("Your Questions and E-mails: ")

    @staticmethod
    def from_summary_text(text: str) -> "FromSummaryTextSegment":
        raw_items = text.split(": ")[1].split(",")
        items = [raw_item.strip() for raw_item in raw_items]
        return EmailSegment(items)


# endregion
# region From Show Notes
def parse_show_notes_segment_data(segment_data: list["Tag"]) -> "BaseSegment|None":
    text = segment_data[0].text

    for segment_class in segment_types["from_notes"]:
        if segment_class.match_string(text):
            return segment_class.from_show_notes(segment_data)

    for segment_class in segment_types["from_summary"]:
        if segment_class.match_string(text):
            return None

    raise ValueError(f"Unknown segment: {text}")


class FromShowNotesSegment(BaseSegment, ABC):
    @staticmethod
    @abstractmethod
    def from_show_notes(segment_data: list["Tag"]) -> "FromShowNotesSegment":
        raise NotImplementedError


@dataclass
class NoisySegment(FromShowNotesSegment):
    last_week_answer: str | None = None

    @staticmethod
    def match_string(text: str) -> bool:
        return text.startswith("Who's That Noisy")

    @staticmethod
    def from_show_notes(segment_data: list["Tag"]) -> "NoisySegment":
        if len(segment_data) == 1:
            return NoisySegment()

        return NoisySegment(last_week_answer=segment_data[1].text.split(": ")[1])


@dataclass
class QuoteSegment(FromShowNotesSegment):
    quote: str

    @staticmethod
    def match_string(text: str) -> bool:
        return text.startswith("Skeptical Quote of the Week")

    @staticmethod
    def from_show_notes(segment_data: list["Tag"]) -> "QuoteSegment":
        return QuoteSegment(segment_data[1].text)


@dataclass
class ScienceOrFictionItem:
    item_number: str
    answer: str
    text: str
    link: str


@dataclass
class ScienceOrFictionSegment(FromShowNotesSegment):
    items: list[ScienceOrFictionItem]

    @staticmethod
    def match_string(text: str) -> bool:
        return "Science or Fiction" in text

    @staticmethod
    def from_show_notes(segment_data: list["Tag"]) -> "ScienceOrFictionSegment":
        raw_items = [i for i in segment_data[1].children if isinstance(i, Tag)]

        items = ScienceOrFictionSegment.process_raw_items(raw_items)

        return ScienceOrFictionSegment(items)

    @staticmethod
    def process_raw_items(raw_items: list["Tag"]) -> list[ScienceOrFictionItem]:
        items: list[ScienceOrFictionItem] = []
        for raw_item in raw_items:
            title = cast(Tag, raw_item.find(class_="science-fiction__item-title")).text
            text = cast(Tag, raw_item.find("p")).text
            answer = cast(Tag, raw_item.find(class_="quiz__answer")).text

            link = cast(Tag, raw_item.find("a"))
            url = cast(str, link["href"])

            items.append(ScienceOrFictionItem(title, answer, text, url))

        return items


@dataclass
class NewsItem:
    topic: str
    link: str


@dataclass
class NewsSegment(FromShowNotesSegment):
    items: list[NewsItem]

    @staticmethod
    def match_string(text: str) -> bool:
        return text.startswith("News Items")

    @staticmethod
    def from_show_notes(segment_data: list["Tag"]) -> "NewsSegment":
        raw_items = [i for i in segment_data[1].children if isinstance(i, Tag)]

        items = NewsSegment.process_raw_items(raw_items)

        return NewsSegment(items)

    @staticmethod
    def process_raw_items(raw_items: list["Tag"]) -> list[NewsItem]:
        items: list[NewsItem] = []
        for raw_item in raw_items:
            a_tag = cast(Tag, raw_item.find("a"))
            link = cast(str, a_tag["href"])

            items.append(NewsItem(raw_item.text, link))

        return items


# endregion


class SegmentTypeMapping(TypedDict):
    from_summary: list[type[FromSummaryTextSegment]]
    from_notes: list[type[FromShowNotesSegment]]


segment_types: SegmentTypeMapping = {
    "from_summary": [QuickieSegment, EmailSegment],
    "from_notes": [NewsSegment, NoisySegment, QuoteSegment, ScienceOrFictionSegment],
}
