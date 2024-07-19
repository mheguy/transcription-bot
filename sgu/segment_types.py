import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import ClassVar

from bs4 import Tag

from sgu.custom_logger import logger
from sgu.helpers import extract_element, string_is_url

SPECIAL_SUMMARY_PATTERNS = [
    "guest rogue",
    "special guest",
    "live from",
    "live recording",
]

Segments = list["BaseSegment"]


# region components
class SegmentSource(Enum):
    LYRICS = "embedded lyrics"
    NOTES = "show notes"
    SUMMARY = "episode summary"


@dataclass
class ScienceOrFictionItem:
    item_number: str
    answer: str
    text: str
    url: str


@dataclass
class NewsItem:
    topic: str
    link: str


# endregion
# region base
@dataclass(kw_only=True)
class BaseSegment(ABC):
    segment_number: int
    source: SegmentSource

    def __str__(self) -> str:
        segment = self._get_segment_number()
        text = self.get_text()
        return f"{segment}<!-- extracted from {self.source} --><br>\n{text}"

    @staticmethod
    @abstractmethod
    def match_string(lowercase_text: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_text(self) -> str:
        raise NotImplementedError

    def _get_segment_number(self) -> str:
        if self.segment_number:
            return f"Segment #{self.segment_number}"

        return "Segment"


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
    def from_lyrics(text: str, segment_number: int) -> "FromLyricsSegment":
        raise NotImplementedError


# endregion
# region concrete
@dataclass(kw_only=True)
class UnknownSegment(BaseSegment):
    text: str

    def get_text(self) -> str:
        return self.text

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        raise NotImplementedError


@dataclass(kw_only=True)
class LogicalFalacySegment(FromSummaryTextSegment):
    def get_text(self) -> str:
        raise NotImplementedError

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return "name that logical fallacy" in lowercase_text

    @staticmethod
    def from_summary_text(text: str) -> "LogicalFalacySegment":
        del text

        return LogicalFalacySegment(segment_number=0, source=SegmentSource.SUMMARY)


@dataclass(kw_only=True)
class QuickieSegment(FromSummaryTextSegment):
    text: str

    def get_text(self) -> str:
        raise NotImplementedError

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return lowercase_text.startswith("quickie with")

    @staticmethod
    def from_summary_text(text: str) -> "QuickieSegment":
        return QuickieSegment(segment_number=0, text=text, source=SegmentSource.SUMMARY)


@dataclass(kw_only=True)
class WhatsTheWordSegment(FromSummaryTextSegment):
    word: str

    def get_text(self) -> str:
        raise NotImplementedError

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return lowercase_text.startswith("what's the word")

    @staticmethod
    def from_summary_text(text: str) -> "WhatsTheWordSegment":
        lines = text.split(":")

        if len(lines) > 1:
            word = lines[1].strip()
        else:
            word = "N/A<!-- Failed to extract word -->"

        return WhatsTheWordSegment(segment_number=0, word=word, source=SegmentSource.SUMMARY)


@dataclass(kw_only=True)
class DumbestThingOfTheWeekSegment(FromLyricsSegment):
    topic: str
    url: str

    def get_text(self) -> str:
        return f"{self.topic}<br>\nLink:{self.url}"

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return lowercase_text.startswith("dumbest thing of the week")

    @staticmethod
    def from_lyrics(text: str, segment_number: int) -> "DumbestThingOfTheWeekSegment":
        lines = text.split("\n")
        url = ""
        topic = ""

        if len(lines) > 1:
            topic = lines[1].strip()

        if len(lines) > 2:  # noqa: PLR2004
            url = lines[2].strip()

        return DumbestThingOfTheWeekSegment(
            segment_number=segment_number,
            topic=topic,
            url=url,
            source=SegmentSource.LYRICS,
        )


@dataclass(kw_only=True)
class SwindlersListSegment(FromSummaryTextSegment):
    topic: str = "N/A<!-- Failed to extract topic -->"

    def get_text(self) -> str:
        raise NotImplementedError

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return bool(re.match(r"swindler.s list", lowercase_text))

    @staticmethod
    def from_summary_text(text: str) -> "SwindlersListSegment":
        return SwindlersListSegment(segment_number=0, topic=text.split(":")[1].strip(), source=SegmentSource.SUMMARY)


@dataclass(kw_only=True)
class ForgottenSuperheroesOfScienceSegment(FromSummaryTextSegment):
    subject: str = "N/A<!-- Failed to extract subject -->"

    def get_text(self) -> str:
        raise NotImplementedError

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return bool(re.match(r"forgotten superhero(es)? of science", lowercase_text))

    @staticmethod
    def from_summary_text(text: str) -> "ForgottenSuperheroesOfScienceSegment":
        lines = text.split(":")
        if len(lines) == 1:
            return ForgottenSuperheroesOfScienceSegment(segment_number=0, source=SegmentSource.SUMMARY)

        return ForgottenSuperheroesOfScienceSegment(
            segment_number=0,
            subject=lines[1].strip(),
            source=SegmentSource.SUMMARY,
        )


@dataclass(kw_only=True)
class NoisySegment(FromShowNotesSegment, FromLyricsSegment):
    valid_splitters: ClassVar[str] = ":-"

    last_week_answer: str = "N/A<!-- Failed to extract last week's answer -->"

    def get_text(self) -> str:
        return f"Last week's answer: {self.last_week_answer}"

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return bool(re.search(r"who.s that noisy", lowercase_text))

    @staticmethod
    def from_show_notes(segment_data: list["Tag"]) -> "NoisySegment":
        if len(segment_data) == 1:
            return NoisySegment(segment_number=0, source=SegmentSource.NOTES)

        for splitter in NoisySegment.valid_splitters:
            if splitter in segment_data[1].text:
                return NoisySegment(
                    segment_number=0,
                    last_week_answer=segment_data[1].text.split(splitter)[1].strip(),
                    source=SegmentSource.NOTES,
                )

        return NoisySegment(segment_number=0, source=SegmentSource.NOTES)

    @staticmethod
    def from_lyrics(text: str, segment_number: int) -> "NoisySegment":
        del text
        return NoisySegment(segment_number=segment_number, source=SegmentSource.NOTES)


@dataclass(kw_only=True)
class QuoteSegment(FromLyricsSegment):
    quote: str
    attribution: str

    def get_text(self) -> str:
        return f"{self.quote}<br>\n{self.attribution}"

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return lowercase_text.startswith("skeptical quote of the week")

    @staticmethod
    def from_show_notes(segment_data: list["Tag"]) -> "QuoteSegment":
        if len(segment_data) > 1:
            quote = segment_data[1].text
        else:
            quote = "N/A<!-- Failed to extract quote -->"

        return QuoteSegment(segment_number=0, quote=quote, attribution="", source=SegmentSource.NOTES)

    @staticmethod
    def from_lyrics(text: str, segment_number: int) -> "QuoteSegment":
        lines = list(filter(None, text.split("\n")[1:]))
        attribution = "<!-- Failed to extract attribution -->"

        if len(lines) == 1:
            logger.warning("Unable to extract quote attribution from lyrics.")
        elif len(lines) == 2:  # noqa: PLR2004
            attribution = lines[1]
        else:
            raise ValueError(f"Unexpected number of lines in segment text: {text}")

        return QuoteSegment(
            segment_number=segment_number,
            quote=lines[0],
            attribution=attribution,
            source=SegmentSource.NOTES,
        )


@dataclass(kw_only=True)
class ScienceOrFictionSegment(FromShowNotesSegment, FromLyricsSegment):
    items: list[ScienceOrFictionItem]
    theme: str | None = None

    def get_text(self) -> str:
        text = f"Theme: {self.theme}<br>\n" if self.theme else ""

        for item in self.items:
            text += f"<p>{item.item_number}<br>\n{item.text}<br>\nAnswer: {item.answer}<br>\nLink: {item.url}<br><p/>\n"

        return text

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return "science or fiction" in lowercase_text

    @staticmethod
    def from_show_notes(segment_data: list["Tag"]) -> "ScienceOrFictionSegment":
        raw_items = [i for i in segment_data[1].children if isinstance(i, Tag)]

        items = ScienceOrFictionSegment.process_raw_items(raw_items)

        return ScienceOrFictionSegment(segment_number=0, items=items, source=SegmentSource.NOTES)

    @staticmethod
    def process_raw_items(raw_items: list["Tag"]) -> list[ScienceOrFictionItem]:
        items: list[ScienceOrFictionItem] = []
        for raw_item in raw_items:
            title_text = extract_element(raw_item, "span", "science-fiction__item-title").text

            p_tag = extract_element(raw_item, "p", "")
            p_text = p_tag.text.strip()

            if better_tag := p_tag.next:
                p_text = better_tag.text.strip()

            answer = extract_element(raw_item, "span", "quiz__answer").text

            a_tag = extract_element(p_tag, "a", "")
            url = a_tag.get("href", "")

            if not isinstance(url, str):
                raise TypeError("Got an unexpected type in url")

            items.append(ScienceOrFictionItem(title_text, answer, p_text, url))

        return items

    @staticmethod
    def from_lyrics(text: str, segment_number: int) -> "ScienceOrFictionSegment":
        lines = text.split("\n")[2:]
        theme = None

        for line in lines:
            if line.lower().startswith("theme:"):
                theme = line.split(":")[1].strip()
                break

        return ScienceOrFictionSegment(
            segment_number=segment_number,
            items=[],
            theme=theme,
            source=SegmentSource.LYRICS,
        )


@dataclass(kw_only=True)
class NewsSegment(FromShowNotesSegment, FromLyricsSegment):
    items: list[NewsItem]

    def get_text(self) -> str:
        return "\n".join([f"{item.topic}<br>\nLink: {item.link}" for item in self.items])

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return lowercase_text.startswith("news item")

    @staticmethod
    def from_show_notes(segment_data: list["Tag"]) -> "NewsSegment":
        show_notes = [i for i in segment_data[1].children if isinstance(i, Tag)]

        items = NewsSegment.process_show_notes(show_notes)

        return NewsSegment(segment_number=0, items=items, source=SegmentSource.NOTES)

    @staticmethod
    def process_show_notes(raw_items: list["Tag"]) -> list[NewsItem]:
        news_items: list[NewsItem] = []

        for raw_item in raw_items:
            url = ""
            if a_tag_with_href := raw_item.select_one('div > a[href]:not([href=""])'):
                href = a_tag_with_href["href"]
                url = href if isinstance(href, str) else href[0]

            news_items.append(NewsItem(raw_item.text, url))

        return news_items

    @staticmethod
    def from_lyrics(text: str, segment_number: int) -> "NewsSegment":
        lines = text.split("\n")[1:]
        news_items: list[NewsItem] = []

        for index, line in enumerate(lines):
            if "news item" in line.lower():
                next_line = lines[index + 1] if index + 1 < len(lines) else ""
                url = next_line if next_line and string_is_url(next_line) else ""
                news_items.append(NewsItem(line, url))

        return NewsSegment(segment_number=segment_number, items=news_items, source=SegmentSource.NOTES)


@dataclass(kw_only=True)
class InterviewSegment(FromShowNotesSegment):
    subject: str

    def get_text(self) -> str:
        raise NotImplementedError

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return lowercase_text.startswith("interview with")

    @staticmethod
    def from_show_notes(segment_data: list["Tag"]) -> "InterviewSegment":
        text = segment_data[0].text
        subject = re.split(r"[w|W]ith", text)[1]

        return InterviewSegment(segment_number=0, subject=subject.strip(":- "), source=SegmentSource.NOTES)


@dataclass(kw_only=True)
class EmailSegment(FromLyricsSegment, FromShowNotesSegment):
    items: list[str]

    def get_text(self) -> str:
        return "<br>\n".join(self.items)

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return lowercase_text.startswith("question #") or all(s in lowercase_text for s in ["your", "question", "mail"])

    @staticmethod
    def from_summary_text(text: str) -> "EmailSegment":
        if ": " not in text:
            return EmailSegment(segment_number=0, items=[], source=SegmentSource.SUMMARY)

        raw_items = text.split(":")[1].split(",")
        items = [raw_item.strip() for raw_item in raw_items]
        return EmailSegment(segment_number=0, items=items, source=SegmentSource.SUMMARY)

    @staticmethod
    def from_show_notes(segment_data: list["Tag"]) -> "EmailSegment":
        text = segment_data[0].text
        if ": " not in text:
            return EmailSegment(segment_number=0, items=[], source=SegmentSource.NOTES)

        raw_items = text.split(":")[1].split(",")
        items = [raw_item.strip() for raw_item in raw_items]
        return EmailSegment(segment_number=0, items=items, source=SegmentSource.NOTES)

    @staticmethod
    def from_lyrics(text: str, segment_number: int) -> "EmailSegment":
        lines = text.split("\n")[1:] + [None]  # sentinel value

        items = []
        question = []

        for line in lines:
            if question and (line is None or line.lower().startswith(("question #", "email #"))):
                items.append("\n".join(question))
                question = []

            if line:
                question.append(line)

        return EmailSegment(segment_number=segment_number, items=items, source=SegmentSource.NOTES)


# endregion
PARSER_SEGMENT_TYPES = (FromLyricsSegment, FromSummaryTextSegment, FromShowNotesSegment)
segment_types = [
    value
    for value in globals().values()
    if isinstance(value, type) and issubclass(value, PARSER_SEGMENT_TYPES) and value not in PARSER_SEGMENT_TYPES
]
