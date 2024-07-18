import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar, Literal, TypedDict

from bs4 import Tag

SPECIAL_SUMMARY_PATTERNS = [
    "guest rogue",
    "special guest",
    "live from",
    "live recording",
]


# region parsers


def parse_lyrics(lyrics: str):
    lyrics = lyrics.replace("\r", "\n")
    pattern = r"(Segment #\d.+?)(?=(?:Segment #\d+|$))"
    lyric_chunks = re.findall(pattern, lyrics, re.DOTALL)

    for lyric_chunk in lyric_chunks:
        ...


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


def is_special_summary_text(text: str) -> bool:
    """Check if the text indicates something about the episode (guest, live, etc.)."""
    return any(pattern in text for pattern in SPECIAL_SUMMARY_PATTERNS)


def get_url_from_tag(item: Tag) -> str:
    url = ""
    if a_tag_with_href := item.select_one('div > a[href]:not([href=""])'):
        href = a_tag_with_href["href"]
        url = href if isinstance(href, str) else href[0]

    return url


# endregion
# region components
@dataclass
class ScienceOrFictionItem:
    item_number: str
    answer: str
    text: str
    url: str


# endregion
# region base
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


class FromSummaryTextSegment(BaseSegment, ABC):
    @staticmethod
    @abstractmethod
    def from_summary_text(text: str) -> "FromSummaryTextSegment":
        raise NotImplementedError


class FromShowNotesSegment(BaseSegment, ABC):
    @staticmethod
    @abstractmethod
    def from_show_notes(segment_data: list["Tag"]) -> "FromShowNotesSegment":
        raise NotImplementedError


class FromLyricsSegment(BaseSegment, ABC):
    @staticmethod
    @abstractmethod
    def from_lyrics(segment_data: list["Tag"]) -> "FromLyricsSegment":
        raise NotImplementedError


# endregion
# region concrete
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
# region mappings
class SegmentTypeMapping(TypedDict):
    from_lyrics: list[type[FromLyricsSegment]]
    from_summary: list[type[FromSummaryTextSegment]]
    from_notes: list[type[FromShowNotesSegment]]


segment_mapping: SegmentTypeMapping = {
    "from_lyrics": [
        c
        for c in globals().values()
        if isinstance(c, type) and issubclass(c, FromLyricsSegment) and c is not FromLyricsSegment
    ],
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
# endregion
