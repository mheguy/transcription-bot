import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, ClassVar

from bs4 import Tag
from jinja2 import Environment, FileSystemLoader

from sgu.config import TEMPLATES_FOLDER
from sgu.custom_logger import logger
from sgu.helpers import find_single_element, string_is_url

SPECIAL_SUMMARY_PATTERNS = [
    "guest rogue",
    "special guest",
    "live from",
    "live recording",
]

Segments = list["BaseSegment"]


# region components
class SegmentSource(Enum):
    """The origin of the segment data."""

    LYRICS = "embedded lyrics"
    NOTES = "show notes"
    SUMMARY = "episode summary"


@dataclass
class ScienceOrFictionItem:
    number: int
    show_notes_text: str
    article_url: str
    sof_result: str

    # From the article URL, we can get the following fields:
    article_title: str = ""  # TODO
    article_publication: str = ""  # TODO


@dataclass
class NewsItem:
    topic: str
    link: str


# endregion
# region base
@dataclass(kw_only=True)
class BaseSegment(ABC):
    """Base for all segments."""

    template_env: ClassVar = Environment(
        block_start_string="((*",
        block_end_string="*))",
        variable_start_string="(((",
        variable_end_string=")))",
        comment_start_string="((=",
        comment_end_string="=))",
        autoescape=True,
        loader=FileSystemLoader(TEMPLATES_FOLDER),
    )

    source: SegmentSource

    def to_wiki(self) -> str:
        """Get the wiki text / section header for the segment."""
        template = self.template_env.get_template(f"{self.template_name}.j2x")
        template_values = self.get_template_values()
        return template.render(**template_values)

    @property
    @abstractmethod
    def template_name(self) -> str:
        """The name of the Jinja2 template file."""
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def match_string(lowercase_text: str) -> bool:
        """Determine if the provided text matches a segment type."""
        raise NotImplementedError

    @abstractmethod
    def get_template_values(self) -> dict[str, Any]:
        """Get the text representation of the segment (for the wiki page)."""
        raise NotImplementedError


class FromSummaryTextSegment(BaseSegment, ABC):
    """A segment whose source is the episode summary."""

    @staticmethod
    @abstractmethod
    def from_summary_text(text: str) -> "FromSummaryTextSegment":
        """Create a segment from the episode summary text."""
        raise NotImplementedError


class FromShowNotesSegment(BaseSegment, ABC):
    """A segment whose source is the show notes."""

    @staticmethod
    @abstractmethod
    def from_show_notes(segment_data: list["Tag"]) -> "FromShowNotesSegment":
        """Create a segment from the show notes."""
        raise NotImplementedError


class FromLyricsSegment(BaseSegment, ABC):
    """A segment whose source is the embedded lyrics."""

    @staticmethod
    @abstractmethod
    def from_lyrics(text: str) -> "FromLyricsSegment":
        """Create a segment from the embedded lyrics."""
        raise NotImplementedError


# endregion
# region concrete
@dataclass(kw_only=True)
class UnknownSegment(BaseSegment):
    """A segment that could not be identified."""

    title: str

    @property
    def template_name(self) -> str:
        return "unknown"

    def get_template_values(self) -> dict[str, Any]:
        return {"title": self.title}

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        raise NotImplementedError


@dataclass(kw_only=True)
class IntroSegment(BaseSegment):
    """The segment that introduces the show and has banter betweeen the rogues."""

    @property
    def template_name(self) -> str:
        raise NotImplementedError

    def get_template_values(self) -> dict[str, Any]:
        return {}

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        raise NotImplementedError


@dataclass(kw_only=True)
class LogicalFalacySegment(FromSummaryTextSegment):
    @property
    def template_name(self) -> str:
        return "logical_falacy"

    def get_template_values(self) -> dict[str, Any]:
        raise NotImplementedError

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return "name that logical fallacy" in lowercase_text

    @staticmethod
    def from_summary_text(text: str) -> "LogicalFalacySegment":
        del text

        return LogicalFalacySegment(source=SegmentSource.SUMMARY)


@dataclass(kw_only=True)
class QuickieSegment(FromLyricsSegment, FromSummaryTextSegment):
    title: str

    @property
    def template_name(self) -> str:
        return "quickie"

    def get_template_values(self) -> dict[str, Any]:
        return {"title": self.title}

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return lowercase_text.startswith("quickie with")

    @staticmethod
    def from_summary_text(text: str) -> "QuickieSegment":
        return QuickieSegment(title=text, source=SegmentSource.SUMMARY)

    @staticmethod
    def from_lyrics(text: str) -> "QuickieSegment":
        return QuickieSegment(title=text, source=SegmentSource.LYRICS)


@dataclass(kw_only=True)
class WhatsTheWordSegment(FromSummaryTextSegment):
    word: str

    @property
    def template_name(self) -> str:
        return "whats_the_word"

    def get_template_values(self) -> dict[str, Any]:
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

        return WhatsTheWordSegment(word=word, source=SegmentSource.SUMMARY)


@dataclass(kw_only=True)
class DumbestThingOfTheWeekSegment(FromLyricsSegment):
    topic: str
    url: str

    @property
    def template_name(self) -> str:
        raise NotImplementedError

    def get_template_values(self) -> dict[str, Any]:
        return {"topic": self.topic, "link": self.url}

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return lowercase_text.startswith("dumbest thing of the week")

    @staticmethod
    def from_lyrics(text: str) -> "DumbestThingOfTheWeekSegment":
        lines = text.split("\n")
        url = ""
        topic = ""

        if len(lines) > 1:
            topic = lines[1].strip()

        if len(lines) > 2:  # noqa: PLR2004
            url = lines[2].strip()

        return DumbestThingOfTheWeekSegment(
            topic=topic,
            url=url,
            source=SegmentSource.LYRICS,
        )


@dataclass(kw_only=True)
class NoisySegment(FromShowNotesSegment, FromLyricsSegment):
    valid_splitters: ClassVar[str] = ":-"

    last_week_answer: str = "N/A<!-- Failed to extract last week's answer -->"

    @property
    def template_name(self) -> str:
        return "noisy"

    def get_template_values(self) -> dict[str, Any]:
        return {"last_week_answer": self.last_week_answer}

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return bool(re.search(r"who.s that noisy", lowercase_text))

    @staticmethod
    def from_show_notes(segment_data: list["Tag"]) -> "NoisySegment":
        if len(segment_data) == 1:
            return NoisySegment(source=SegmentSource.NOTES)

        for splitter in NoisySegment.valid_splitters:
            if splitter in segment_data[1].text:
                return NoisySegment(
                    last_week_answer=segment_data[1].text.split(splitter)[1].strip(),
                    source=SegmentSource.NOTES,
                )

        return NoisySegment(source=SegmentSource.NOTES)

    @staticmethod
    def from_lyrics(text: str) -> "NoisySegment":
        del text
        return NoisySegment(source=SegmentSource.NOTES)


@dataclass(kw_only=True)
class QuoteSegment(FromLyricsSegment):
    quote: str
    attribution: str

    @property
    def template_name(self) -> str:
        return "quote"

    def get_template_values(self) -> dict[str, Any]:
        return {"quote": self.quote, "attribution": self.attribution}

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return lowercase_text.startswith("skeptical quote of the week")

    @staticmethod
    def from_show_notes(segment_data: list["Tag"]) -> "QuoteSegment":
        if len(segment_data) > 1:
            quote = segment_data[1].text
        else:
            quote = "N/A<!-- Failed to extract quote -->"

        return QuoteSegment(quote=quote, attribution="", source=SegmentSource.NOTES)

    @staticmethod
    def from_lyrics(text: str) -> "QuoteSegment":
        lines = list(filter(None, text.split("\n")[1:]))
        attribution = "<!-- Failed to extract attribution -->"

        if len(lines) == 1:
            logger.warning("Unable to extract quote attribution from lyrics.")
        elif len(lines) == 2:  # noqa: PLR2004
            attribution = lines[1]
        else:
            raise ValueError(f"Unexpected number of lines in segment text: {text}")

        return QuoteSegment(
            quote=lines[0],
            attribution=attribution,
            source=SegmentSource.NOTES,
        )


@dataclass(kw_only=True)
class ScienceOrFictionSegment(FromShowNotesSegment, FromLyricsSegment):
    items: list[ScienceOrFictionItem]
    theme: str | None = None

    @property
    def template_name(self) -> str:
        return "science_or_fiction"

    def get_template_values(self) -> dict[str, Any]:
        return {"items": self.items, "theme": self.theme}

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return "science or fiction" in lowercase_text

    @staticmethod
    def from_show_notes(segment_data: list["Tag"]) -> "ScienceOrFictionSegment":
        raw_items = [i for i in segment_data[1].children if isinstance(i, Tag)]

        items = ScienceOrFictionSegment.process_raw_items(raw_items)

        return ScienceOrFictionSegment(items=items, source=SegmentSource.NOTES)

    @staticmethod
    def process_raw_items(raw_items: list["Tag"]) -> list[ScienceOrFictionItem]:
        items: list[ScienceOrFictionItem] = []

        science_items = 1
        for raw_item in raw_items:
            title_text = find_single_element(raw_item, "span", "science-fiction__item-title").text
            match = re.search(r"(\d+)", title_text)
            if not match:
                raise ValueError(f"Failed to extract item number from: {title_text}")

            item_number = int(match.group(1))

            p_tag = find_single_element(raw_item, "p", "")
            p_text = p_tag.text.strip()

            if better_tag := p_tag.next:
                p_text = better_tag.text.strip()

            answer = find_single_element(raw_item, "span", "quiz__answer").text

            a_tag = find_single_element(p_tag, "a", "")
            url = a_tag.get("href", "")

            if not isinstance(url, str):
                raise TypeError("Got an unexpected type in url")

            if answer.lower() == "science":
                sof_result = f"science{science_items}"
                science_items += 1

            items.append(ScienceOrFictionItem(item_number, p_text, url, sof_result))

        return items

    @staticmethod
    def from_lyrics(text: str) -> "ScienceOrFictionSegment":
        lines = text.split("\n")[2:]
        theme = None

        for line in lines:
            if line.lower().startswith("theme:"):
                theme = line.split(":")[1].strip()
                break

        return ScienceOrFictionSegment(
            items=[],
            theme=theme,
            source=SegmentSource.LYRICS,
        )


@dataclass(kw_only=True)
class NewsSegment(FromShowNotesSegment, FromLyricsSegment):
    items: list[NewsItem]

    @property
    def template_name(self) -> str:
        return "news"

    def get_template_values(self) -> dict[str, Any]:
        return {"items": self.items}

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return lowercase_text.startswith("news item")

    @staticmethod
    def from_show_notes(segment_data: list["Tag"]) -> "NewsSegment":
        show_notes = [i for i in segment_data[1].children if isinstance(i, Tag)]

        items = NewsSegment._process_show_notes(show_notes)

        return NewsSegment(items=items, source=SegmentSource.NOTES)

    @staticmethod
    def from_lyrics(text: str) -> "NewsSegment":
        lines = text.split("\n")[1:]
        news_items: list[NewsItem] = []

        for index, line in enumerate(lines):
            if "news item" in line.lower():
                next_line = lines[index + 1] if index + 1 < len(lines) else ""
                url = next_line if next_line and string_is_url(next_line) else ""
                news_items.append(NewsItem(line, url))

        return NewsSegment(items=news_items, source=SegmentSource.NOTES)

    @staticmethod
    def _process_show_notes(raw_items: list["Tag"]) -> list[NewsItem]:
        news_items: list[NewsItem] = []

        for raw_item in raw_items:
            url = ""
            if a_tag_with_href := raw_item.select_one('div > a[href]:not([href=""])'):
                href = a_tag_with_href["href"]
                url = href if isinstance(href, str) else href[0]

            news_items.append(NewsItem(raw_item.text, url))

        return news_items


@dataclass(kw_only=True)
class InterviewSegment(FromShowNotesSegment):
    subject: str

    @property
    def template_name(self) -> str:
        raise NotImplementedError

    def get_template_values(self) -> dict[str, Any]:
        raise NotImplementedError

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return lowercase_text.startswith("interview with")

    @staticmethod
    def from_show_notes(segment_data: list["Tag"]) -> "InterviewSegment":
        text = segment_data[0].text
        subject = re.split(r"[w|W]ith", text)[1]

        return InterviewSegment(subject=subject.strip(":- "), source=SegmentSource.NOTES)


@dataclass(kw_only=True)
class EmailSegment(FromLyricsSegment, FromShowNotesSegment):
    items: list[str]

    @property
    def template_name(self) -> str:
        raise NotImplementedError

    def get_template_values(self) -> dict[str, Any]:
        raise NotImplementedError
        return "<br>\n".join(self.items)

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return lowercase_text.startswith("question #") or all(s in lowercase_text for s in ["your", "question", "mail"])

    @staticmethod
    def from_summary_text(text: str) -> "EmailSegment":
        if ": " not in text:
            return EmailSegment(items=[], source=SegmentSource.SUMMARY)

        raw_items = text.split(":")[1].split(",")
        items = [raw_item.strip() for raw_item in raw_items]
        return EmailSegment(items=items, source=SegmentSource.SUMMARY)

    @staticmethod
    def from_show_notes(segment_data: list["Tag"]) -> "EmailSegment":
        text = segment_data[0].text
        if ": " not in text:
            return EmailSegment(items=[], source=SegmentSource.NOTES)

        raw_items = text.split(":")[1].split(",")
        items = [raw_item.strip() for raw_item in raw_items]
        return EmailSegment(items=items, source=SegmentSource.NOTES)

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

        return EmailSegment(items=items, source=SegmentSource.NOTES)


# @dataclass(kw_only=True)
# class ForgottenSuperheroesOfScienceSegment(FromSummaryTextSegment):
#     subject: str = "N/A<!-- Failed to extract subject -->"

#     @property
#     def template_name(self) -> str:
#         raise NotImplementedError

#     def get_template_values(self) -> dict[str, Any]:
#         raise NotImplementedError

#     @staticmethod
#     def match_string(lowercase_text: str) -> bool:
#         return bool(re.match(r"forgotten superhero(es)? of science", lowercase_text))

#     @staticmethod
#     def from_summary_text(text: str) -> "ForgottenSuperheroesOfScienceSegment":
#         lines = text.split(":")
#         if len(lines) == 1:
#             return ForgottenSuperheroesOfScienceSegment(source=SegmentSource.SUMMARY)

#         return ForgottenSuperheroesOfScienceSegment(
#             subject=lines[1].strip(),
#             source=SegmentSource.SUMMARY,
#         )


# @dataclass(kw_only=True)
# class SwindlersListSegment(FromSummaryTextSegment):
#     topic: str = "N/A<!-- Failed to extract topic -->"

#     @property
#     def template_name(self) -> str:
#         raise NotImplementedError

#     def get_template_values(self) -> dict[str, Any]:
#         raise NotImplementedError

#     @staticmethod
#     def match_string(lowercase_text: str) -> bool:
#         return bool(re.match(r"swindler.s list", lowercase_text))

#     @staticmethod
#     def from_summary_text(text: str) -> "SwindlersListSegment":
#         return SwindlersListSegment(topic=text.split(":")[1].strip(), source=SegmentSource.SUMMARY)


# endregion
PARSER_SEGMENT_TYPES = (FromLyricsSegment, FromSummaryTextSegment, FromShowNotesSegment)
segment_types = [
    value
    for value in globals().values()
    if isinstance(value, type) and issubclass(value, PARSER_SEGMENT_TYPES) and value not in PARSER_SEGMENT_TYPES
]