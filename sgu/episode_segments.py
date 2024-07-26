import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar
from urllib.parse import urlparse

from bs4 import Tag

from sgu.global_logger import logger
from sgu.helpers import are_strings_in_string, find_single_element, get_article_title, string_is_url
from sgu.template_environment import template_env
from sgu.transcript_formatting import format_time, format_transcript_for_wiki

if TYPE_CHECKING:
    from sgu.transcription import DiarizedTranscript

SPECIAL_SUMMARY_PATTERNS = [
    "guest rogue",
    "special guest",
    "live from",
    "live recording",
]

Segments = list["BaseSegment"]


# region components
@dataclass(kw_only=True)
class ScienceOrFictionItem:
    number: int
    show_notes_text: str
    article_url: str
    sof_result: str

    article_title: str
    article_publication: str


# endregion
# region base
@dataclass(kw_only=True)
class BaseSegment(ABC):
    """Base for all segments."""

    start_time: float | None = None
    transcript: "DiarizedTranscript" = field(default_factory=list)

    def to_wiki(self) -> str:
        """Get the wiki text / section header for the segment."""
        template = template_env.get_template(f"{self.template_name}.j2x")
        template_values = self.get_template_values()
        return template.render(
            start_time=format_time(self.start_time),
            transcript=format_transcript_for_wiki(self.transcript),
            **template_values,
        )

    @property
    @abstractmethod
    def template_name(self) -> str:
        """The name of the Jinja2 template file."""
        raise NotImplementedError

    @property
    @abstractmethod
    def llm_prompt(self) -> str:
        """A prompt to help an LLM identify a transition between segments."""
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

    @abstractmethod
    def get_start_time(self, transcript: "DiarizedTranscript") -> float | None:
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
    extra_text: str

    @property
    def template_name(self) -> str:
        return "unknown"

    @property
    def llm_prompt(self) -> str:
        return f"Please identify the start of the segment whose title is: {self.title}, {self.extra_text}"

    def get_template_values(self) -> dict[str, Any]:
        return {"title": self.title}

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        raise NotImplementedError

    def get_start_time(self, transcript: "DiarizedTranscript") -> float | None:
        for chunk in transcript:
            if are_strings_in_string(self.title.split(), chunk["text"].lower()):
                return chunk["start"]

            if are_strings_in_string(self.extra_text.split(), chunk["text"].lower()):
                return chunk["start"]

        return None

    @staticmethod
    def create(text: str) -> "UnknownSegment":
        lines = text.split("\n")
        title = lines[0].strip()

        if len(lines) > 1:
            extra_text = "\n".join(lines[1:])
        else:
            extra_text = ""

        return UnknownSegment(title=title, extra_text=extra_text)


@dataclass(kw_only=True)
class IntroSegment(BaseSegment):
    """The segment that introduces the show and has banter betweeen the rogues."""

    @property
    def template_name(self) -> str:
        return "intro"

    @property
    def llm_prompt(self) -> str:
        raise NotImplementedError

    def get_template_values(self) -> dict[str, Any]:
        return {}

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        raise NotImplementedError

    def get_start_time(self, transcript: "DiarizedTranscript") -> float | None:
        del transcript
        return 0.0


@dataclass(kw_only=True)
class LogicalFalacySegment(FromSummaryTextSegment):
    @property
    def template_name(self) -> str:
        return "logical_falacy"

    @property
    def llm_prompt(self) -> str:
        return "Please identify the start of the 'name that logical fallacy' segment."

    def get_template_values(self) -> dict[str, Any]:
        raise NotImplementedError

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return "name that logical fallacy" in lowercase_text

    def get_start_time(self, transcript: "DiarizedTranscript") -> float | None:
        for chunk in transcript:
            if are_strings_in_string(["name", "logical", "fallacy"], chunk["text"].lower()):
                return chunk["start"]

        return None

    @staticmethod
    def from_summary_text(text: str) -> "LogicalFalacySegment":
        del text

        return LogicalFalacySegment()


@dataclass(kw_only=True)
class QuickieSegment(FromLyricsSegment, FromSummaryTextSegment):
    title: str
    subject: str

    @property
    def template_name(self) -> str:
        return "quickie"

    @property
    def llm_prompt(self) -> str:
        return f"Please find the start of the 'quickie' segment: {self.title}. The subject is: {self.subject}"

    def get_template_values(self) -> dict[str, Any]:
        return {"title": self.title, "subject": self.subject}

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return lowercase_text.startswith("quickie with")

    def get_start_time(self, transcript: "DiarizedTranscript") -> float | None:
        for chunk in transcript:
            if are_strings_in_string(["quickie", "with"], chunk["text"].lower()):
                return chunk["start"]

            if are_strings_in_string(self.subject.split(), chunk["text"].lower()):
                return chunk["start"]

        return None

    @staticmethod
    def from_summary_text(text: str) -> "QuickieSegment":
        return QuickieSegment(title=text, subject="")

    @staticmethod
    def from_lyrics(text: str) -> "QuickieSegment":
        lines = text.split("\n")
        title = lines[0].strip()

        if len(lines) > 1:
            subject = lines[1].strip()
        else:
            subject = ""

        return QuickieSegment(title=title, subject=subject)


@dataclass(kw_only=True)
class WhatsTheWordSegment(FromSummaryTextSegment):
    word: str

    @property
    def template_name(self) -> str:
        return "whats_the_word"

    @property
    def llm_prompt(self) -> str:
        return (
            "Please find the start of the 'what's the word' segment."
            "This is typically introduced by Steve asking Cara for the word."
        )

    def get_template_values(self) -> dict[str, Any]:
        raise NotImplementedError

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return lowercase_text.startswith("what's the word")

    def get_start_time(self, transcript: "DiarizedTranscript") -> float | None:
        for chunk in transcript:
            if re.match(r"what.?s the word", chunk["text"].lower()):
                return chunk["start"]

            if self.word.lower() in chunk["text"].lower():
                return chunk["start"]

        return None

    @staticmethod
    def from_summary_text(text: str) -> "WhatsTheWordSegment":
        lines = text.split(":")

        if len(lines) > 1:
            word = lines[1].strip()
        else:
            word = "N/A<!-- Failed to extract word -->"

        return WhatsTheWordSegment(word=word)


@dataclass(kw_only=True)
class TikTokSegment(FromLyricsSegment):
    title: str
    url: str

    @property
    def template_name(self) -> str:
        return "tiktok"

    @property
    def llm_prompt(self) -> str:
        return f"Please identify the start of the 'from tiktok' segment. The topic is: {self.title}"

    def get_template_values(self) -> dict[str, Any]:
        return {"title": self.title, "url": self.url}

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return lowercase_text.startswith("from tiktok")

    def get_start_time(self, transcript: "DiarizedTranscript") -> float | None:
        for chunk in transcript:
            if are_strings_in_string(self.title.split(), chunk["text"].lower()):
                return chunk["start"]

        return None

    @staticmethod
    def from_lyrics(text: str) -> "TikTokSegment":
        lines = text.split("\n")
        lines = list(filter(None, lines))
        title = lines[1].strip()
        url = lines[2].strip()

        if not title:
            raise ValueError(f"Failed to extract title from: {text}")

        if not url or not string_is_url(url):
            raise ValueError(f"Failed to extract valid URL from: {text}")

        return TikTokSegment(title=title, url=url)


@dataclass(kw_only=True)
class DumbestThingOfTheWeekSegment(FromLyricsSegment):
    topic: str
    url: str
    article_title: str
    article_publication: str

    @property
    def template_name(self) -> str:
        raise NotImplementedError

    @property
    def llm_prompt(self) -> str:
        return (
            "Please identify the start of the 'dumbest thing of the week' segment."
            f"This segment is about: {self.topic}"
        )

    def get_template_values(self) -> dict[str, Any]:
        return {
            "topic": self.topic,
            "url": self.url,
            "article_title": self.article_title,
            "article_publication": self.article_publication,
        }

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return lowercase_text.startswith("dumbest thing of the week")

    def get_start_time(self, transcript: "DiarizedTranscript") -> float | None:
        for segment in transcript:
            if are_strings_in_string(["dumb", "thing", "of", "the", "week"], segment["text"].lower()):
                return segment["start"]

        return None

    @staticmethod
    def from_lyrics(text: str) -> "DumbestThingOfTheWeekSegment":
        lines = text.split("\n")

        topic = ""
        if len(lines) > 1:
            topic = lines[1].strip()

        url = ""
        if len(lines) > 2:  # noqa: PLR2004
            url = lines[2].strip()

        article_publication = ""
        if url:
            article_publication = urlparse(url).netloc
            article_title = get_article_title(url)

        return DumbestThingOfTheWeekSegment(
            topic=topic, url=url, article_publication=article_publication, article_title=article_title
        )


@dataclass(kw_only=True)
class NoisySegment(FromShowNotesSegment, FromLyricsSegment):
    valid_splitters: ClassVar[str] = ":-"

    last_week_answer: str = "<!-- Failed to extract last week's answer -->"

    @property
    def template_name(self) -> str:
        return "noisy"

    @property
    def llm_prompt(self) -> str:
        return "Please identify the start of the 'who's that noisy' segment."

    def get_template_values(self) -> dict[str, Any]:
        return {"last_week_answer": self.last_week_answer}

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return bool(re.search(r"who.s that noisy", lowercase_text))

    def get_start_time(self, transcript: "DiarizedTranscript") -> float | None:
        for segment in transcript:
            if are_strings_in_string(["who", "that", "noisy"], segment["text"].lower()):
                return segment["start"]

        return None

    @staticmethod
    def from_show_notes(segment_data: list["Tag"]) -> "NoisySegment":
        if len(segment_data) == 1:
            return NoisySegment()

        for splitter in NoisySegment.valid_splitters:
            if splitter in segment_data[1].text:
                return NoisySegment(
                    last_week_answer=segment_data[1].text.split(splitter)[1].strip(),
                )

        return NoisySegment()

    @staticmethod
    def from_lyrics(text: str) -> "NoisySegment":
        del text
        return NoisySegment()


@dataclass(kw_only=True)
class QuoteSegment(FromLyricsSegment):
    quote: str
    attribution: str

    @property
    def template_name(self) -> str:
        return "quote"

    @property
    def llm_prompt(self) -> str:
        return "Please identify the start of the 'quote' segment. This is usually Steve asking Evan for the quote."

    def get_template_values(self) -> dict[str, Any]:
        return {"quote": self.quote, "attribution": self.attribution}

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return lowercase_text.startswith("skeptical quote of the week")

    def get_start_time(self, transcript: "DiarizedTranscript") -> float | None:
        for segment in transcript:
            text = segment["text"].lower()
            if "quote" in text and segment["speaker"] == "Steve":
                return segment["start"]

        return None

    @staticmethod
    def from_show_notes(segment_data: list["Tag"]) -> "QuoteSegment":
        if len(segment_data) > 1:
            quote = segment_data[1].text
        else:
            quote = "N/A<!-- Failed to extract quote -->"

        return QuoteSegment(quote=quote, attribution="")

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
        )


@dataclass(kw_only=True)
class ScienceOrFictionSegment(FromShowNotesSegment, FromLyricsSegment):
    items: list[ScienceOrFictionItem]
    theme: str | None = None

    @property
    def template_name(self) -> str:
        return "science_or_fiction"

    @property
    def llm_prompt(self) -> str:
        return "Please identify the start of the 'science or fiction' segment."

    def get_template_values(self) -> dict[str, Any]:
        return {"items": self.items, "theme": self.theme}

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return "science or fiction" in lowercase_text

    def get_start_time(self, transcript: "DiarizedTranscript") -> float | None:
        for segment in transcript:
            if "time for science or fiction" in segment["text"].lower():
                return segment["start"]

        return None

    @staticmethod
    def from_show_notes(segment_data: list["Tag"]) -> "ScienceOrFictionSegment":
        raw_items = [i for i in segment_data[1].children if isinstance(i, Tag)]

        items = ScienceOrFictionSegment.process_raw_items(raw_items)

        return ScienceOrFictionSegment(items=items)

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

            p_tag = find_single_element(raw_item, "p", None)
            p_text = p_tag.text.strip()

            if better_tag := p_tag.next:
                p_text = better_tag.text.strip()

            answer = find_single_element(raw_item, "span", "quiz__answer").text

            a_tag = find_single_element(p_tag, "a", None)
            url = a_tag.get("href", "")

            if not isinstance(url, str):
                raise TypeError("Got an unexpected type in url")

            publication = ""
            if url:
                publication = urlparse(url).netloc
                article_title = get_article_title(url)

            if answer.lower() == "science":
                sof_result = f"science{science_items}"
                science_items += 1
            else:
                sof_result = "fiction"

            items.append(
                ScienceOrFictionItem(
                    number=item_number,
                    show_notes_text=p_text,
                    article_url=url,
                    sof_result=sof_result,
                    article_publication=publication,
                    article_title=article_title,
                )
            )

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
        )


@dataclass(kw_only=True)
class NewsItem(BaseSegment):
    item_number: int
    topic: str
    url: str

    article_title: str
    article_publication: str

    @property
    def template_name(self) -> str:
        return "news"

    @property
    def llm_prompt(self) -> str:
        return f"Please identify the start of the news segment whose topic is: {self.article_title}"

    def get_template_values(self) -> dict[str, Any]:
        return {
            "item_number": self.item_number,
            "topic": self.topic,
            "url": self.url,
            "article_title": self.article_title,
            "article_publication": self.article_publication,
        }

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        raise NotImplementedError

    def get_start_time(self, transcript: "DiarizedTranscript") -> float | None:
        del transcript

        return None


@dataclass(kw_only=True)
class NewsMetaSegment(FromLyricsSegment):
    """This "metasegment" contains multiple news segments. It is expanded in segment_joiner."""

    news_segments: list[NewsItem]

    @property
    def template_name(self) -> str:
        raise NotImplementedError

    @property
    def llm_prompt(self) -> str:
        raise NotImplementedError

    def get_template_values(self) -> dict[str, Any]:
        raise NotImplementedError

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return lowercase_text.startswith("news item")

    def get_start_time(self, transcript: "DiarizedTranscript") -> float | None:
        raise NotImplementedError

    @staticmethod
    def from_lyrics(text: str) -> "NewsMetaSegment":
        lines = text.split("\n")[1:]

        items: list[NewsItem] = []
        item_counter = 0

        for index, line in enumerate(lines):
            if "news item" in line.lower():
                item_counter += 1

                url = ""
                next_index = index + 1
                if next_index < len(lines) and string_is_url(lines[next_index]):
                    url = lines[next_index]

                publication = ""
                if url:
                    publication = urlparse(url).netloc
                    article_title = get_article_title(url)

                match = re.match(r"news item #\d+ . (.+)", line, re.IGNORECASE)
                if not match:
                    raise ValueError(f"Failed to extract news topic from: {line}")
                topic = match.group(1).strip()

                items.append(
                    NewsItem(
                        item_number=item_counter,
                        topic=topic,
                        url=url,
                        article_publication=publication,
                        article_title=article_title,
                    )
                )

        return NewsMetaSegment(news_segments=items)


@dataclass(kw_only=True)
class InterviewSegment(FromShowNotesSegment):
    name: str

    @property
    def template_name(self) -> str:
        raise NotImplementedError

    @property
    def llm_prompt(self) -> str:
        return "Please identity the beginning of the interview segment."

    def get_template_values(self) -> dict[str, Any]:
        raise NotImplementedError

    def get_start_time(self, transcript: "DiarizedTranscript") -> float | None:
        raise NotImplementedError

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return lowercase_text.startswith("interview with")

    @staticmethod
    def from_show_notes(segment_data: list["Tag"]) -> "InterviewSegment":
        text = segment_data[0].text
        name = re.split(r"[w|W]ith", text)[1]

        return InterviewSegment(name=name.strip(":- "))


@dataclass(kw_only=True)
class EmailSegment(FromLyricsSegment, FromShowNotesSegment):
    items: list[str]

    @property
    def template_name(self) -> str:
        return "email"

    @property
    def llm_prompt(self) -> str:
        return "Please identify the start of the 'email' segment."

    def get_template_values(self) -> dict[str, Any]:
        return {"items": self.items}

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return lowercase_text.startswith("question #") or all(s in lowercase_text for s in ["your", "question", "mail"])

    def get_start_time(self, transcript: "DiarizedTranscript") -> float | None:
        for segment in transcript:
            if "mail" in segment["text"].lower() and segment["speaker"] == "Steve":
                return segment["start"]

        return None

    @staticmethod
    def from_summary_text(text: str) -> "EmailSegment":
        if ": " not in text:
            return EmailSegment(items=[])

        raw_items = text.split(":")[1].split(",")
        items = [raw_item.strip() for raw_item in raw_items]
        return EmailSegment(items=items)

    @staticmethod
    def from_show_notes(segment_data: list["Tag"]) -> "EmailSegment":
        text = segment_data[0].text
        if ": " not in text:
            return EmailSegment(items=[])

        raw_items = text.split(":")[1].split(",")
        items = [raw_item.strip() for raw_item in raw_items]
        return EmailSegment(items=items)

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

        return EmailSegment(items=items)


@dataclass(kw_only=True)
class ForgottenSuperheroesOfScienceSegment(FromSummaryTextSegment):
    subject: str = "N/A<!-- Failed to extract subject -->"

    @property
    def template_name(self) -> str:
        raise NotImplementedError

    @property
    def llm_prompt(self) -> str:
        return "Please identify the start of the 'forgotten superheroes of science' segment."

    def get_template_values(self) -> dict[str, Any]:
        raise NotImplementedError

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return bool(re.match(r"forgotten superhero(es)? of science", lowercase_text))

    def get_start_time(self, transcript: "DiarizedTranscript") -> float | None:
        for chunk in transcript:
            if are_strings_in_string(["forgotten", "hero", "science"], chunk["text"].lower()):
                return chunk["start"]

        return None

    @staticmethod
    def from_summary_text(text: str) -> "ForgottenSuperheroesOfScienceSegment":
        lines = text.split(":")
        if len(lines) == 1:
            return ForgottenSuperheroesOfScienceSegment()

        return ForgottenSuperheroesOfScienceSegment(
            subject=lines[1].strip(),
        )


@dataclass(kw_only=True)
class SwindlersListSegment(FromSummaryTextSegment):
    topic: str = "N/A<!-- Failed to extract topic -->"

    @property
    def template_name(self) -> str:
        raise NotImplementedError

    @property
    def llm_prompt(self) -> str:
        raise NotImplementedError

    def get_template_values(self) -> dict[str, Any]:
        raise NotImplementedError

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return bool(re.match(r"swindler.s list", lowercase_text))

    def get_start_time(self, transcript: "DiarizedTranscript") -> float | None:
        for chunk in transcript:
            if are_strings_in_string(["swindler", "list"], chunk["text"].lower()):
                return chunk["start"]

        return None

    @staticmethod
    def from_summary_text(text: str) -> "SwindlersListSegment":
        return SwindlersListSegment(topic=text.split(":")[1].strip())


# endregion
PARSER_SEGMENT_TYPES = (FromLyricsSegment, FromSummaryTextSegment, FromShowNotesSegment)
segment_types = [
    value
    for value in globals().values()
    if isinstance(value, type) and issubclass(value, PARSER_SEGMENT_TYPES) and value not in PARSER_SEGMENT_TYPES
]
