import math
import re
from abc import ABC, abstractmethod
from dataclasses import field
from typing import Any, ClassVar, TypeVar
from urllib.parse import urlparse

from bs4 import Tag
from pydantic.dataclasses import dataclass

from transcription_bot.data_models import DiarizedTranscript
from transcription_bot.global_logger import logger
from transcription_bot.helpers import are_strings_in_string, find_single_element, get_article_title, string_is_url
from transcription_bot.templating import get_template

T = TypeVar("T", bound="BaseSegment")
Segments = list["BaseSegment"]


SPECIAL_SUMMARY_PATTERNS = [
    "guest rogue",
    "special guest",
    "live from",
    "live recording",
]


# region components
@dataclass(kw_only=True)
class ScienceOrFictionItem:
    number: int
    show_notes_text: str
    article_url: str | None
    sof_result: str

    article_title: str | None
    article_publication: str | None


# endregion
# region base
@dataclass(kw_only=True)
class BaseSegment(ABC):
    """Base for all segments."""

    start_time: float | None = None
    end_time: float = math.inf
    transcript: DiarizedTranscript = field(default_factory=list)

    @property
    @abstractmethod
    def template_name(self) -> str:
        """The name of the Jinja2 template file."""

    @property
    @abstractmethod
    def llm_prompt(self) -> str:
        """A prompt to help an LLM identify a transition between segments."""

    @property
    @abstractmethod
    def wiki_anchor_tag(self) -> str:
        """The tag used in the wiki page to anchor to the segment."""

    @staticmethod
    @abstractmethod
    def match_string(lowercase_text: str) -> bool:
        """Determine if the provided text matches a segment type."""

    @abstractmethod
    def get_template_values(self) -> dict[str, Any]:
        """Get the text representation of the segment (for the wiki page)."""

    @abstractmethod
    def get_start_time(self, transcript: DiarizedTranscript) -> float | None:
        """Get the text representation of the segment (for the wiki page)."""

    @property
    def duration(self) -> float:
        """Provide the duration of the segment in minutes."""
        if self.start_time is None:
            return 0

        return (self.end_time - self.start_time) / 60

    def to_wiki(self) -> str:
        """Get the wiki text / section header for the segment."""
        template = get_template(self.template_name)
        template_values = self.get_template_values()
        return template.render(
            wiki_anchor=self.wiki_anchor_tag,
            start_time=format_time(self.start_time),
            transcript=format_transcript_for_wiki(self.transcript),
            **template_values,
        )


@dataclass(kw_only=True)
class NonNewsSegmentMixin:
    """Mixin for segments that are not news / in each episode.

    This is used to populate the "other" section of the episode entry.
    """

    title: str


class FromSummaryTextSegment(BaseSegment, ABC):
    """A segment whose source is the episode summary."""

    @staticmethod
    @abstractmethod
    def from_summary_text(text: str) -> "FromSummaryTextSegment":
        """Create a segment from the episode summary text."""


class FromShowNotesSegment(BaseSegment, ABC):
    """A segment whose source is the show notes."""

    @staticmethod
    @abstractmethod
    def from_show_notes(segment_data: list["Tag"]) -> "FromShowNotesSegment":
        """Create a segment from the show notes."""


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
    url: str | None

    @property
    def template_name(self) -> str:
        return "unknown"

    @property
    def llm_prompt(self) -> str:
        return f"Please identify the start of the segment whose title is: {self.title}, {self.extra_text}"

    @property
    def wiki_anchor_tag(self) -> str:
        raise NotImplementedError

    def get_template_values(self) -> dict[str, Any]:
        return {"title": self.title, "extra_text": self.extra_text, "url": self.url}

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        raise NotImplementedError

    def get_start_time(self, transcript: DiarizedTranscript) -> float | None:
        for chunk in transcript:
            if are_strings_in_string(self.title.split(), chunk["text"].lower()):
                return chunk["start"]

            if are_strings_in_string(self.extra_text.split(), chunk["text"].lower()):
                return chunk["start"]

        return None

    @staticmethod
    def create(text: str) -> "UnknownSegment":
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        lines += [""] * (1 - len(lines))
        title, *extra_lines = lines

        extra_text = ""
        url = None

        for line in extra_lines:
            if string_is_url(line):
                url = line
            else:
                extra_text += line

        return UnknownSegment(title=title, extra_text=extra_text, url=url)


@dataclass(kw_only=True)
class IntroSegment(BaseSegment):
    """The segment that introduces the show and has banter betweeen the rogues."""

    @property
    def template_name(self) -> str:
        return "intro"

    @property
    def llm_prompt(self) -> str:
        raise NotImplementedError

    @property
    def wiki_anchor_tag(self) -> str:
        return "intro"

    def get_template_values(self) -> dict[str, Any]:
        return {}

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        raise NotImplementedError

    def get_start_time(self, transcript: DiarizedTranscript) -> float | None:
        del transcript
        return 0.0


@dataclass(kw_only=True)
class OutroSegment(BaseSegment):
    @property
    def template_name(self) -> str:
        return "outro"

    @property
    def llm_prompt(self) -> str:
        return "Please find the start of the outro. This is typically where Steve says 'Skeptics' Guide to the Universe is produced by SGU Productions'"

    @property
    def wiki_anchor_tag(self) -> str:
        raise NotImplementedError

    def get_template_values(self) -> dict[str, Any]:
        return {}

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        raise NotImplementedError

    def get_start_time(self, transcript: DiarizedTranscript) -> float | None:
        for chunk in transcript:
            if are_strings_in_string(
                ["skeptic", "guide", "to", "the", "universe", "produced", "by", "sgu", "productions"],
                chunk["text"].lower(),
            ):
                return chunk["start"]

        return None


@dataclass(kw_only=True)
class LogicalFallacySegment(FromLyricsSegment, NonNewsSegmentMixin):
    topic: str

    title: str = "Name That Logical Fallacy"

    @property
    def template_name(self) -> str:
        return "logical_fallacy"

    @property
    def llm_prompt(self) -> str:
        return "Please identify the start of the 'name that logical fallacy' segment."

    @property
    def wiki_anchor_tag(self) -> str:
        return "ntlf"

    def get_template_values(self) -> dict[str, Any]:
        return {"topic": self.topic}

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return "name that logical fallacy" in lowercase_text

    def get_start_time(self, transcript: DiarizedTranscript) -> float | None:
        for chunk in transcript:
            if are_strings_in_string(["name", "logical", "fallacy"], chunk["text"].lower()):
                return chunk["start"]

        return None

    @staticmethod
    def from_lyrics(text: str) -> "LogicalFallacySegment":
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        lines += [""] * (2 - len(lines))
        _segment_name, *topic = lines

        return LogicalFallacySegment(topic=" ".join(topic))


@dataclass(kw_only=True)
class QuickieSegment(FromLyricsSegment, NonNewsSegmentMixin):
    title: str
    subject: str
    url: str
    article_title: str | None
    article_publication: str | None

    @property
    def template_name(self) -> str:
        return "quickie"

    @property
    def llm_prompt(self) -> str:
        return f"Please find the start of the 'quickie' segment: {self.title}. The subject is: {self.subject}"

    @property
    def wiki_anchor_tag(self) -> str:
        return "quickie"

    def get_template_values(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "subject": self.subject,
            "url": self.url,
            "article_title": self.article_title,
            "article_publication": self.article_publication,
        }

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return lowercase_text.startswith("quickie with")

    def get_start_time(self, transcript: DiarizedTranscript) -> float | None:
        for chunk in transcript:
            if are_strings_in_string(["quickie", "with"], chunk["text"].lower()):
                return chunk["start"]

            if are_strings_in_string(self.subject.split(), chunk["text"].lower()):
                return chunk["start"]

        return None

    @staticmethod
    def from_lyrics(text: str) -> "QuickieSegment":
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        lines += [""] * (3 - len(lines))
        title, subject, url, *extra = lines

        if extra:
            logger.warning(f"Unexpected extra lines in quickie segment: {extra}")

        article_publication = None
        article_title = None
        if url:
            article_publication = urlparse(url).netloc
            article_title = get_article_title(url) or url

        return QuickieSegment(
            title=title,
            subject=subject,
            url=url,
            article_title=article_title,
            article_publication=article_publication,
        )


@dataclass(kw_only=True)
class WhatsTheWordSegment(FromLyricsSegment, NonNewsSegmentMixin):
    word: str

    title: str = "What's the Word?"

    @property
    def template_name(self) -> str:
        return "whats_the_word"

    @property
    def llm_prompt(self) -> str:
        return (
            "Please find the start of the 'what's the word' segment."
            "This is typically introduced by Steve asking Cara for the word."
        )

    @property
    def wiki_anchor_tag(self) -> str:
        return "wtw"

    def get_template_values(self) -> dict[str, Any]:
        return {"word": self.word}

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return bool(re.match(r"what.s the word", lowercase_text))

    def get_start_time(self, transcript: DiarizedTranscript) -> float | None:
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

    @staticmethod
    def from_lyrics(text: str) -> "WhatsTheWordSegment":
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        lines += [""] * (2 - len(lines))
        _segment_name, word, *extra = lines

        if extra:
            logger.warning(f"Unexpected extra lines in whatstheword segment: {extra}")

        if not word:
            raise ValueError(f"Failed to extract title from: {text}")

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

    @property
    def wiki_anchor_tag(self) -> str:
        return "tiktok"

    def get_template_values(self) -> dict[str, Any]:
        return {"title": self.title, "url": self.url}

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return lowercase_text.startswith("from tiktok")

    def get_start_time(self, transcript: DiarizedTranscript) -> float | None:
        for chunk in transcript:
            if are_strings_in_string(self.title.split(), chunk["text"].lower()):
                return chunk["start"]

        return None

    @staticmethod
    def from_lyrics(text: str) -> "TikTokSegment":
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        lines += [""] * (3 - len(lines))
        _segment_name, title, url, *extra = lines

        if extra:
            logger.warning(f"Unexpected extra lines in tiktok segment: {extra}")

        if not title:
            raise ValueError(f"Failed to extract title from: {text}")

        if not url or not string_is_url(url):
            raise ValueError(f"Failed to extract valid URL from: {text}")

        return TikTokSegment(title=title, url=url)


@dataclass(kw_only=True)
class DumbestThingOfTheWeekSegment(FromLyricsSegment, NonNewsSegmentMixin):
    topic: str
    url: str
    article_title: str | None
    article_publication: str | None

    title: str = "Dumbest Thing of the Week"

    @property
    def template_name(self) -> str:
        return "dumbest"

    @property
    def llm_prompt(self) -> str:
        return (
            "Please identify the start of the 'dumbest thing of the week' segment."
            f"This segment is about: {self.topic}"
        )

    @property
    def wiki_anchor_tag(self) -> str:
        return "dumbest"

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

    def get_start_time(self, transcript: DiarizedTranscript) -> float | None:
        for segment in transcript:
            if are_strings_in_string(["dumb", "thing", "of", "the", "week"], segment["text"].lower()):
                return segment["start"]

        return None

    @staticmethod
    def from_lyrics(text: str) -> "DumbestThingOfTheWeekSegment":
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        lines += [""] * (3 - len(lines))
        _segment_name, topic, url, *extra = lines

        if extra:
            logger.warning(f"Unexpected extra lines in dumbest thing of the week segment: {extra}")

        article_publication = None
        article_title = None
        if url:
            article_publication = urlparse(url).netloc
            article_title = get_article_title(url) or url

        return DumbestThingOfTheWeekSegment(
            topic=topic,
            url=url,
            article_publication=article_publication,
            article_title=article_title,
        )


@dataclass(kw_only=True)
class NoisySegment(FromLyricsSegment, FromShowNotesSegment):
    valid_splitters: ClassVar[str] = ":-"

    last_week_answer: str = "<!-- Failed to extract last week's answer -->"

    @property
    def template_name(self) -> str:
        return "noisy"

    @property
    def llm_prompt(self) -> str:
        return "Please identify the start of the 'who's that noisy' segment."

    @property
    def wiki_anchor_tag(self) -> str:
        return "wtn"

    def get_template_values(self) -> dict[str, Any]:
        return {"last_week_answer": self.last_week_answer}

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return bool(re.search(r"who.s that noisy", lowercase_text))

    def get_start_time(self, transcript: DiarizedTranscript) -> float | None:
        for segment in transcript:
            if are_strings_in_string(["who", "that", "noisy"], segment["text"].lower()):
                return segment["start"]

        return None

    @staticmethod
    def from_show_notes(segment_data: list["Tag"]) -> "NoisySegment":
        """Create a NoisySegment that will be merged with the lyrics segment."""
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

    @property
    def wiki_anchor_tag(self) -> str:
        return "qow"

    def get_template_values(self) -> dict[str, Any]:
        return {"quote": self.quote, "attribution": self.attribution}

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return lowercase_text.startswith("skeptical quote of the week")

    def get_start_time(self, transcript: DiarizedTranscript) -> float | None:
        for segment in transcript:
            text = segment["text"].lower()
            if "quote" in text and segment["speaker"] == "Steve":
                return segment["start"]

        return None

    @staticmethod
    def from_lyrics(text: str) -> "QuoteSegment":
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        lines += [""] * (3 - len(lines))
        _segment_name, quote, attribution, *extra = lines

        if extra:
            logger.warning(f"Unexpected extra lines in quote segment: {extra}")

        if not quote:
            logger.warning("Unable to extract quote attribution from lyrics.")

        return QuoteSegment(quote=quote, attribution=attribution)


@dataclass(kw_only=True)
class ScienceOrFictionSegment(FromLyricsSegment, FromShowNotesSegment):
    items: list[ScienceOrFictionItem]
    theme: str | None = None

    @property
    def template_name(self) -> str:
        return "science_or_fiction"

    @property
    def llm_prompt(self) -> str:
        return "Please identify the start of the 'science or fiction' segment."

    @property
    def wiki_anchor_tag(self) -> str:
        return "theme"

    def get_template_values(self) -> dict[str, Any]:
        return {"items": self.items, "theme": self.theme}

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return "science or fiction" in lowercase_text

    def get_start_time(self, transcript: DiarizedTranscript) -> float | None:
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

            try:
                a_tag = find_single_element(p_tag, "a", None)
                article_url = a_tag.get("href", "")
                if not isinstance(article_url, str):
                    raise TypeError("Got an unexpected type in url")
            except ValueError:
                article_url = ""

            publication = None
            article_title = None
            if article_url:
                publication = urlparse(article_url).netloc
                article_title = get_article_title(article_url) or article_url

            if answer.lower() == "science":
                sof_result = f"science{science_items}"
                science_items += 1
            else:
                sof_result = "fiction"

            items.append(
                ScienceOrFictionItem(
                    number=item_number,
                    show_notes_text=p_text,
                    article_url=article_url,
                    sof_result=sof_result,
                    article_publication=publication,
                    article_title=article_title,
                )
            )

        return items

    @staticmethod
    def from_lyrics(text: str) -> "ScienceOrFictionSegment":
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        theme = None

        for line in lines:
            if line.lower().startswith("theme:"):
                theme = line.split(":")[1].strip()
                break

        return ScienceOrFictionSegment(items=[], theme=theme)


@dataclass(kw_only=True)
class NewsItem(BaseSegment):
    item_number: int
    topic: str
    url: str | None

    article_title: str | None
    article_publication: str | None

    @property
    def template_name(self) -> str:
        return "news"

    @property
    def llm_prompt(self) -> str:
        return f"Please identify the start of the news segment whose topic is: {self.article_title or self.topic}"

    @property
    def wiki_anchor_tag(self) -> str:
        raise NotImplementedError

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

    def get_start_time(self, transcript: DiarizedTranscript) -> float | None:
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

    @property
    def wiki_anchor_tag(self) -> str:
        raise NotImplementedError

    def get_template_values(self) -> dict[str, Any]:
        raise NotImplementedError

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return lowercase_text.startswith("news item")

    def get_start_time(self, transcript: DiarizedTranscript) -> float | None:
        raise NotImplementedError

    @staticmethod
    def from_lyrics(text: str) -> "NewsMetaSegment":
        lines = text.split("\n")[1:]

        items: list[NewsItem] = []
        item_counter = 0

        for index, line in enumerate(lines):
            if "news item" in line.lower():
                item_counter += 1

                url = None
                next_index = index + 1
                if next_index < len(lines) and string_is_url(lines[next_index]):
                    url = lines[next_index]

                publication = None
                article_title = None
                if url:
                    publication = urlparse(url).netloc
                    article_title = get_article_title(url) or url

                match = re.match(r"news item ?#?\d+\s*.\s*(.+)", line, re.IGNORECASE)
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
class InterviewSegment(FromLyricsSegment, FromShowNotesSegment):
    name: str
    url: str

    @property
    def template_name(self) -> str:
        return "interview"

    @property
    def llm_prompt(self) -> str:
        return f"Please identity the beginning of the interview with {self.name}."

    @property
    def wiki_anchor_tag(self) -> str:
        return "interview"

    def get_template_values(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "url": self.url,
        }

    def get_start_time(self, transcript: DiarizedTranscript) -> float | None:
        for chunk in transcript:
            if are_strings_in_string(["go", "to", "interview"], chunk["text"].lower()):
                return chunk["start"]

        return None

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return lowercase_text.startswith("interview with")

    @staticmethod
    def from_show_notes(segment_data: list["Tag"]) -> "InterviewSegment":
        text = segment_data[0].text
        name = re.split(r"[w|W]ith", text)[1]

        return InterviewSegment(name=name.strip(":- "), url="")

    @staticmethod
    def from_lyrics(text: str) -> "InterviewSegment":
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        lines += [""] * (2 - len(lines))
        name, url, *extra = lines

        if extra:
            logger.warning(f"Unexpected extra lines in interview segment: {extra}")

        return InterviewSegment(
            name=name.replace("Interview with", "").strip(),
            url=url,
        )


@dataclass(kw_only=True)
class EmailSegment(FromLyricsSegment, FromShowNotesSegment):
    items: list[str]

    @property
    def template_name(self) -> str:
        return "email"

    @property
    def llm_prompt(self) -> str:
        return "Please identify the start of the 'email' segment."

    @property
    def wiki_anchor_tag(self) -> str:
        return "email"

    def get_template_values(self) -> dict[str, Any]:
        return {"items": self.items}

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return lowercase_text.startswith("question #") or all(s in lowercase_text for s in ["your", "question", "mail"])

    def get_start_time(self, transcript: DiarizedTranscript) -> float | None:
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
        lines = [line.strip() for line in text.split("\n") if line.strip()][1:] + [None]  # sentinel value

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
class ForgottenSuperheroesOfScienceSegment(FromLyricsSegment, FromSummaryTextSegment, NonNewsSegmentMixin):
    subject: str = "N/A<!-- Failed to extract subject -->"

    title: str = "Forgotten Superheroes of Science"

    @property
    def template_name(self) -> str:
        raise NotImplementedError

    @property
    def llm_prompt(self) -> str:
        return "Please identify the start of the 'forgotten superheroes of science' segment."

    @property
    def wiki_anchor_tag(self) -> str:
        raise NotImplementedError

    def get_template_values(self) -> dict[str, Any]:
        raise NotImplementedError

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return bool(re.match(r"forgotten superhero(es)? of science", lowercase_text))

    def get_start_time(self, transcript: DiarizedTranscript) -> float | None:
        for chunk in transcript:
            if are_strings_in_string(["forgotten", "hero", "science"], chunk["text"].lower()):
                return chunk["start"]

        return None

    @staticmethod
    def from_summary_text(text: str) -> "ForgottenSuperheroesOfScienceSegment":
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        lines += [""] * (1 - len(lines))
        subject, *_ = lines

        return ForgottenSuperheroesOfScienceSegment(subject=subject)

    @staticmethod
    def from_lyrics(text: str) -> "ForgottenSuperheroesOfScienceSegment":
        raise NotImplementedError


@dataclass(kw_only=True)
class SwindlersListSegment(FromLyricsSegment, FromSummaryTextSegment, NonNewsSegmentMixin):
    topic: str = "N/A<!-- Failed to extract topic -->"

    title: str = "Swindler's List"

    @property
    def template_name(self) -> str:
        raise NotImplementedError

    @property
    def llm_prompt(self) -> str:
        raise NotImplementedError

    @property
    def wiki_anchor_tag(self) -> str:
        raise NotImplementedError

    def get_template_values(self) -> dict[str, Any]:
        raise NotImplementedError

    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return bool(re.match(r"swindler.s list", lowercase_text))

    def get_start_time(self, transcript: DiarizedTranscript) -> float | None:
        for chunk in transcript:
            if are_strings_in_string(["swindler", "list"], chunk["text"].lower()):
                return chunk["start"]

        return None

    @staticmethod
    def from_summary_text(text: str) -> "SwindlersListSegment":
        return SwindlersListSegment(topic=text.split(":")[1].strip())

    @staticmethod
    def from_lyrics(text: str) -> "SwindlersListSegment":
        raise NotImplementedError


# endregion
# region formatters


def _trim_whitespace(transcript: DiarizedTranscript) -> DiarizedTranscript:
    for chunk in transcript:
        chunk["text"] = chunk["text"].strip()

    return transcript


def _join_speaker_transcription_chunks(transcript: DiarizedTranscript) -> DiarizedTranscript:
    current_speaker = None

    speaker_chunks: DiarizedTranscript = []
    for chunk in transcript:
        if chunk["speaker"] != current_speaker:
            speaker_chunks.append(chunk)
            current_speaker = chunk["speaker"]
        else:
            speaker_chunks[-1]["text"] += " " + chunk["text"]
            speaker_chunks[-1]["end"] = chunk["end"]

    return speaker_chunks


def _abbreviate_speakers(transcript: DiarizedTranscript) -> None:
    for chunk in transcript:
        if chunk["speaker"] == "Voice-over":
            continue

        if "SPEAKER_" in chunk["speaker"]:
            name = "US#" + chunk["speaker"].split("_")[1]
            chunk["speaker"] = name
        else:
            chunk["speaker"] = chunk["speaker"][0]


def format_transcript_for_wiki(transcript: DiarizedTranscript) -> str:
    """Format the transcript for the wiki."""
    transcript = _trim_whitespace(transcript)
    transcript = _join_speaker_transcription_chunks(transcript)
    _abbreviate_speakers(transcript)

    text_chunks = [f"'''{ts_chunk['speaker']}:''' {ts_chunk['text']}" for ts_chunk in transcript]

    return "\n\n".join(text_chunks)


def format_time(time: float | None) -> str:
    """Format a float time to h:mm:ss or mm:ss if < 1 hour."""
    if not time:
        return "???"

    hour_count = int(time) // 3600

    hour = ""
    if hour_count:
        hour = f"{hour_count}:"

    minutes = f"{int(time) // 60 % 60:02d}:"
    seconds = f"{int(time) % 60:02d}"

    return f"{hour}{minutes}{seconds}"


# endregion
# region helpers
def get_first_segment_of_type(segments: Segments, segment_type: type[T]) -> "T | None":
    """Get the first segment of a given type from a list of segments."""
    for segment in segments:
        if isinstance(segment, segment_type):
            return segment

    return None


# endregion
_PARSER_SEGMENT_TYPES = (FromLyricsSegment, FromSummaryTextSegment, FromShowNotesSegment)
segment_types = [
    value
    for value in globals().values()
    if isinstance(value, type) and issubclass(value, _PARSER_SEGMENT_TYPES) and value not in _PARSER_SEGMENT_TYPES
]
