import itertools
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, Literal, TypedDict

from bs4 import Tag

if TYPE_CHECKING:
    from sgu.rss_feed import PodcastFeedEntry
    from sgu.show_notes import ShowNotesData

EPISODE_NUMBER = {"value": 0}  # TODO Debug code

SPECIAL_SUMMARY_PATTERNS = [
    "guest rogue",
    "special guest",
    "live from",
    "live recording",
]


def create_segments(feed_data: "PodcastFeedEntry", notes_data: "ShowNotesData") -> "list[BaseSegment]":
    print("Creating segments...")

    notes_segments = [parse_show_notes_segment_data(seg_data) for seg_data in notes_data.segment_data]

    feed_segments = [create_segment_from_summary_text(line.strip()) for line in feed_data.summary.split(";")]

    segments = [seg for seg in itertools.chain(notes_segments, feed_segments) if seg is not None]
    print(f"Created {len(segments)} segments.")

    return segments


def is_special_summary_text(text: str) -> bool:
    """Check if the text indicates something about the episode (guest, live, etc.)."""
    return any(pattern in text for pattern in SPECIAL_SUMMARY_PATTERNS)


class BaseSegment(ABC):
    @staticmethod
    @abstractmethod
    def match_string(lowercase_text: str) -> bool:
        raise NotImplementedError


@dataclass
class UnknownSegment(BaseSegment):
    text: str
    source: Literal["notes", "summary"]

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        del lowercase_text
        return True


# region From Summary Text
def create_segment_from_summary_text(text: str) -> "BaseSegment|None":
    lower_text = text.lower()

    for segment_class in segment_mapping["from_summary"]:
        if segment_class.match_string(lower_text):
            return segment_class.from_summary_text(text)

    for segment_class in segment_mapping["from_notes"]:
        if segment_class.match_string(lower_text):
            return None

    if is_special_summary_text(lower_text):
        return None

    return UnknownSegment(text, "summary")


class FromSummaryTextSegment(BaseSegment, ABC):
    @staticmethod
    @abstractmethod
    def from_summary_text(text: str) -> "FromSummaryTextSegment":
        raise NotImplementedError


@dataclass
class LogicalFalacySegment(FromSummaryTextSegment):
    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return "name that logical fallacy" in lowercase_text

    @staticmethod
    def from_summary_text(text: str) -> "LogicalFalacySegment":
        del text

        return LogicalFalacySegment()


@dataclass
class QuickieSegment(FromSummaryTextSegment):
    text: str

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return lowercase_text.startswith("quickie with")

    @staticmethod
    def from_summary_text(text: str) -> "QuickieSegment":
        return QuickieSegment(text)


@dataclass
class WhatsTheWordSegment(FromSummaryTextSegment):
    word: str = "(Unable to extract word)"

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return lowercase_text.startswith("what's the word")

    @staticmethod
    def from_summary_text(text: str) -> "WhatsTheWordSegment":
        split_text = text.split(":")
        if len(split_text) == 1:
            return WhatsTheWordSegment()

        return WhatsTheWordSegment(split_text[1].strip())


@dataclass
class DumbestThingOfTheWeekSegment(FromSummaryTextSegment):
    topic: str = "(Unable to extract topic)"

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return lowercase_text.startswith("dumbest thing of the week")

    @staticmethod
    def from_summary_text(text: str) -> "DumbestThingOfTheWeekSegment":
        split_text = text.split(":")
        if len(split_text) == 1:
            return DumbestThingOfTheWeekSegment()

        return DumbestThingOfTheWeekSegment(split_text[1].strip())


@dataclass
class SwindlersListSegment(FromSummaryTextSegment):
    topic: str = "(Unable to extract topic)"

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return bool(re.match(r"swindler.s list", lowercase_text))

    @staticmethod
    def from_summary_text(text: str) -> "SwindlersListSegment":
        return SwindlersListSegment(text.split(":")[1].strip())


@dataclass
class ForgottenSuperheroesOfScienceSegment(FromSummaryTextSegment):
    subject: str = "(Unable to extract subject)"

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return bool(re.match(r"forgotten superhero(es)? of science", lowercase_text))

    @staticmethod
    def from_summary_text(text: str) -> "ForgottenSuperheroesOfScienceSegment":
        split_text = text.split(":")
        if len(split_text) == 1:
            return ForgottenSuperheroesOfScienceSegment()

        return ForgottenSuperheroesOfScienceSegment(split_text[1].strip())


# endregion
# region From Show Notes
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


class FromShowNotesSegment(BaseSegment, ABC):
    @staticmethod
    @abstractmethod
    def from_show_notes(segment_data: list["Tag"]) -> "FromShowNotesSegment":
        raise NotImplementedError


@dataclass
class NoisySegment(FromShowNotesSegment):
    valid_splitters: ClassVar[str] = ":-"

    last_week_answer: str | None = None

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return bool(re.search(r"who.s that noisy", lowercase_text))

    @staticmethod
    def from_show_notes(segment_data: list["Tag"]) -> "NoisySegment":
        if len(segment_data) == 1:
            return NoisySegment()

        for splitter in NoisySegment.valid_splitters:
            if splitter in segment_data[1].text:
                return NoisySegment(segment_data[1].text.split(splitter)[1].strip())

        return NoisySegment()


@dataclass
class QuoteSegment(FromShowNotesSegment):
    quote: str

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return lowercase_text.startswith("skeptical quote of the week")

    @staticmethod
    def from_show_notes(segment_data: list["Tag"]) -> "QuoteSegment":
        if len(segment_data) == 1:
            return QuoteSegment("Unable to extract quote from show notes.")

        return QuoteSegment(segment_data[1].text)


@dataclass
class ScienceOrFictionItem:
    item_number: str
    answer: str
    text: str
    url: str


@dataclass
class ScienceOrFictionSegment(FromShowNotesSegment):
    items: list[ScienceOrFictionItem]

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return "science or fiction" in lowercase_text

    @staticmethod
    def from_show_notes(segment_data: list["Tag"]) -> "ScienceOrFictionSegment":
        raw_items = [i for i in segment_data[1].children if isinstance(i, Tag)]

        items = ScienceOrFictionSegment.process_raw_items(raw_items)

        return ScienceOrFictionSegment(items)

    @staticmethod
    def process_raw_items(raw_items: list["Tag"]) -> list[ScienceOrFictionItem]:
        items: list[ScienceOrFictionItem] = []
        for raw_item in raw_items:
            title_tag = Tag, raw_item.find(class_="science-fiction__item-title")
            title = title_tag.text if isinstance(title_tag, Tag) else ""

            p_tag = Tag, raw_item.find("p")
            text = p_tag.text if isinstance(p_tag, Tag) else ""

            answer_tag = raw_item.find(class_="quiz__answer")
            answer = answer_tag.text if isinstance(answer_tag, Tag) else ""

            url = get_url_from_tag(raw_item)

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
    def match_string(lowercase_text: str) -> bool:
        return lowercase_text.startswith("news item")

    @staticmethod
    def from_show_notes(segment_data: list["Tag"]) -> "NewsSegment":
        raw_items = [i for i in segment_data[1].children if isinstance(i, Tag)]

        items = NewsSegment.process_raw_items(raw_items)

        return NewsSegment(items)

    @staticmethod
    def process_raw_items(raw_items: list["Tag"]) -> list[NewsItem]:
        return [NewsItem(raw_item.text, get_url_from_tag(raw_item)) for raw_item in raw_items]


@dataclass
class InterviewSegment(FromShowNotesSegment):
    subject: str

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return lowercase_text.startswith("interview with")

    @staticmethod
    def from_show_notes(segment_data: list["Tag"]) -> "InterviewSegment":
        text = segment_data[0].text
        subject = re.split(r"[w|W]ith", text)[1]

        return InterviewSegment(subject.strip(":- "))


# endregion
# region Hybrid Segments
@dataclass
class EmailSegment(FromSummaryTextSegment, FromShowNotesSegment):
    items: list[str]

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return lowercase_text.startswith("question #") or all(s in lowercase_text for s in ["your", "question", "mail"])

    @staticmethod
    def from_summary_text(text: str) -> "EmailSegment":
        if ": " not in text:
            return EmailSegment([])

        raw_items = text.split(":")[1].split(",")
        items = [raw_item.strip() for raw_item in raw_items]
        return EmailSegment(items)

    @staticmethod
    def from_show_notes(segment_data: list["Tag"]) -> "EmailSegment":
        text = segment_data[0].text
        if ": " not in text:
            return EmailSegment([])

        raw_items = text.split(":")[1].split(",")
        items = [raw_item.strip() for raw_item in raw_items]
        return EmailSegment(items)


# endregion


def get_url_from_tag(item: Tag) -> str:
    url = ""
    if a_tag_with_href := item.select_one('div > a[href]:not([href=""])'):
        href = a_tag_with_href["href"]
        url = href if isinstance(href, str) else href[0]

    return url


class SegmentTypeMapping(TypedDict):
    from_summary: list[type[FromSummaryTextSegment]]
    from_notes: list[type[FromShowNotesSegment]]


segment_mapping: SegmentTypeMapping = {
    "from_summary": [
        c
        for c in globals().values()
        if isinstance(c, type) and issubclass(c, FromSummaryTextSegment) and c is not FromSummaryTextSegment
    ],
    "from_notes": [
        c
        for c in globals().values()
        if isinstance(c, type) and issubclass(c, FromShowNotesSegment) and c is not FromShowNotesSegment
    ],
}
