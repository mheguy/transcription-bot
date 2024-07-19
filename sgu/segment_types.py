import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar, Literal

from bs4 import Tag

from sgu.custom_logger import logger
from sgu.helpers import string_is_url
from sgu.parsers.soup_helpers import get_url_from_tag

SPECIAL_SUMMARY_PATTERNS = [
    "guest rogue",
    "special guest",
    "live from",
    "live recording",
]

Segments = list["BaseSegment"]


# region components
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
class BaseSegment(ABC):
    @abstractmethod
    def __str__(self) -> str:
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def match_string(lowercase_text: str) -> bool:
        raise NotImplementedError


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
    def from_lyrics(text: str) -> "FromLyricsSegment":
        raise NotImplementedError


# endregion
# region concrete
@dataclass
class UnknownSegment(BaseSegment):
    text: str
    source: Literal["lyrics", "notes", "summary"]

    def __str__(self) -> str:
        return self.text

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        raise NotImplementedError


@dataclass
class LogicalFalacySegment(FromSummaryTextSegment):
    def __str__(self) -> str:
        # TODO
        pass

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

    def __str__(self) -> str:
        # TODO
        pass

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return lowercase_text.startswith("quickie with")

    @staticmethod
    def from_summary_text(text: str) -> "QuickieSegment":
        return QuickieSegment(text)


@dataclass
class WhatsTheWordSegment(FromSummaryTextSegment):
    word: str = "(Unable to extract word)"

    def __str__(self) -> str:
        # TODO
        pass

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
class DumbestThingOfTheWeekSegment(FromSummaryTextSegment, FromLyricsSegment):
    topic: str = "(Unable to extract topic)"
    url: str = "(Unable to extract url)"

    def __str__(self) -> str:
        # TODO
        pass

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return lowercase_text.startswith("dumbest thing of the week")

    @staticmethod
    def from_summary_text(text: str) -> "DumbestThingOfTheWeekSegment":
        split_text = text.split(":")
        if len(split_text) == 1:
            return DumbestThingOfTheWeekSegment()

        return DumbestThingOfTheWeekSegment(split_text[1].strip())

    @staticmethod
    def from_lyrics(text: str) -> "FromLyricsSegment":
        split_text = text.split("\n")

        dispatch = {
            1: lambda: DumbestThingOfTheWeekSegment(),
            2: lambda: DumbestThingOfTheWeekSegment(split_text[1].strip()),
            3: lambda: DumbestThingOfTheWeekSegment(split_text[1].strip(), split_text[2].strip()),
        }

        if len(split_text) in dispatch:
            return dispatch[len(split_text)]()

        raise ValueError(f"Unexpected number of lines in segment text: {text}")


@dataclass
class SwindlersListSegment(FromSummaryTextSegment):
    topic: str = "(Unable to extract topic)"

    def __str__(self) -> str:
        # TODO
        pass

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return bool(re.match(r"swindler.s list", lowercase_text))

    @staticmethod
    def from_summary_text(text: str) -> "SwindlersListSegment":
        return SwindlersListSegment(text.split(":")[1].strip())


@dataclass
class ForgottenSuperheroesOfScienceSegment(FromSummaryTextSegment):
    subject: str = "(Unable to extract subject)"

    def __str__(self) -> str:
        # TODO
        pass

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
class NoisySegment(FromShowNotesSegment, FromLyricsSegment):
    valid_splitters: ClassVar[str] = ":-"

    last_week_answer: str | None = None

    def __str__(self) -> str:
        # TODO
        pass

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

    @staticmethod
    def from_lyrics(text: str) -> "NoisySegment":
        del text
        return NoisySegment()


@dataclass
class QuoteSegment(FromLyricsSegment):
    quote: str
    attribution: str = ""

    def __str__(self) -> str:
        # TODO
        pass

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return lowercase_text.startswith("skeptical quote of the week")

    @staticmethod
    def from_show_notes(segment_data: list["Tag"]) -> "QuoteSegment":
        if len(segment_data) == 1:
            return QuoteSegment("Unable to extract quote from show notes.")

        return QuoteSegment(segment_data[1].text)

    @staticmethod
    def from_lyrics(text: str) -> "QuoteSegment":
        lines = list(filter(None, text.split("\n")[1:]))
        if len(lines) == 1:
            logger.warning("Unable to extract quote attribution from lyrics.")
            return QuoteSegment(lines[0])

        if len(lines) == 2:  # noqa: PLR2004
            return QuoteSegment(lines[0], lines[1])

        raise ValueError(f"Unexpected number of lines in segment text: {text}")


@dataclass
class ScienceOrFictionSegment(FromShowNotesSegment, FromLyricsSegment):
    items: list[ScienceOrFictionItem]
    theme: str | None = None

    def __str__(self) -> str:
        # TODO
        pass

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

    @staticmethod
    def from_lyrics(text: str) -> "ScienceOrFictionSegment":
        lines = text.split("\n")[2:]
        theme = None

        for line in lines:
            if line.lower().startswith("theme:"):
                theme = line.split(":")[1].strip()
                break

        return ScienceOrFictionSegment([], theme=theme)


@dataclass
class NewsSegment(FromShowNotesSegment, FromLyricsSegment):
    items: list[NewsItem]

    def __str__(self) -> str:
        # TODO
        pass

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return lowercase_text.startswith("news item")

    @staticmethod
    def from_show_notes(segment_data: list["Tag"]) -> "NewsSegment":
        show_notes = [i for i in segment_data[1].children if isinstance(i, Tag)]

        items = NewsSegment.process_show_notes(show_notes)

        return NewsSegment(items)

    @staticmethod
    def process_show_notes(raw_items: list["Tag"]) -> list[NewsItem]:
        return [NewsItem(raw_item.text, get_url_from_tag(raw_item)) for raw_item in raw_items]

    @staticmethod
    def from_lyrics(text: str) -> "NewsSegment":
        lines = text.split("\n")[1:]
        news_items: list[NewsItem] = []

        for index, line in enumerate(lines):
            if "news item" in line.lower():
                next_line = lines[index + 1] if index + 1 < len(lines) else ""
                url = next_line if next_line and string_is_url(next_line) else ""
                news_items.append(NewsItem(line, url))

        return NewsSegment(news_items)


@dataclass
class InterviewSegment(FromShowNotesSegment):
    subject: str

    def __str__(self) -> str:
        # TODO
        pass

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return lowercase_text.startswith("interview with")

    @staticmethod
    def from_show_notes(segment_data: list["Tag"]) -> "InterviewSegment":
        text = segment_data[0].text
        subject = re.split(r"[w|W]ith", text)[1]

        return InterviewSegment(subject.strip(":- "))


@dataclass
class EmailSegment(FromLyricsSegment, FromShowNotesSegment):
    items: list[str]

    def __str__(self) -> str:
        # TODO
        pass

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

    @staticmethod
    def from_lyrics(text: str) -> "EmailSegment":
        lines = text.split("\n")[1:] + [None]  # sentinel value

        items = []
        question = []

        for line in lines:
            if question and (line is None or line.lower().startswith(("question #", "email #"))):
                items.append("\n".join(question))
                question = []

            if line:
                question.append(line)

        return EmailSegment(items)


# endregion
PARSER_SEGMENT_TYPES = (FromLyricsSegment, FromSummaryTextSegment, FromShowNotesSegment)
segment_types = [
    value
    for value in globals().values()
    if isinstance(value, type) and issubclass(value, PARSER_SEGMENT_TYPES) and value not in PARSER_SEGMENT_TYPES
]
