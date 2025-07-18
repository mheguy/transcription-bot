import re
from typing import Any, ClassVar, override
from urllib.parse import urlparse

from bs4 import Tag
from loguru import logger
from pydantic.dataclasses import dataclass

from transcription_bot.models.episode_segments.base import (
    BaseSegment,
    FromLyricsSegment,
    FromShowNotesSegment,
    FromSummaryTextSegment,
    NonNewsSegmentMixin,
)
from transcription_bot.models.simple_models import DiarizedTranscript
from transcription_bot.utils.exceptions import StringMatchError
from transcription_bot.utils.helpers import are_strings_in_string, get_article_title, string_is_url


@dataclass(kw_only=True)
class DumbestThingOfTheWeekSegment(FromLyricsSegment, NonNewsSegmentMixin):
    topic: str
    url: str

    title: str = "Dumbest Thing of the Week"

    @property
    @override
    def template_name(self) -> str:
        return "dumbest"

    @property
    @override
    def llm_prompt(self) -> str:
        return (
            "Please identify the start of the 'dumbest thing of the week' segment."
            + f"This segment is about: {self.topic}"
        )

    @property
    @override
    def wiki_anchor_tag(self) -> str:
        return "dumbest"

    @override
    def get_template_values(self) -> dict[str, Any]:
        article_publication = None
        article_title = None
        if self.url:
            article_publication = urlparse(self.url).netloc
            article_title = get_article_title(self.url) or self.url

        return {
            "topic": self.topic,
            "url": self.url,
            "article_title": article_title,
            "article_publication": article_publication,
        }

    @override
    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return lowercase_text.startswith("dumbest thing of the week")

    @override
    def get_start_time(self, transcript: DiarizedTranscript) -> float | None:
        for chunk in transcript:
            if are_strings_in_string(["dumb", "thing", "of", "the", "week"], chunk["text"].lower()):
                return chunk["start"]

        return None

    @override
    @staticmethod
    def from_lyrics(text: str) -> "DumbestThingOfTheWeekSegment":
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        lines += [""] * (3 - len(lines))
        _segment_name, topic, url, *extra = lines

        if extra:
            logger.warning(f"Unexpected extra lines in dumbest thing of the week segment: {extra}")

        return DumbestThingOfTheWeekSegment(
            topic=topic,
            url=url,
        )


@dataclass(kw_only=True)
class EmailSegment(FromLyricsSegment, FromShowNotesSegment):
    items: list[str]

    @property
    @override
    def template_name(self) -> str:
        return "email"

    @property
    @override
    def llm_prompt(self) -> str:
        return "Please identify the start of the 'email' segment."

    @property
    @override
    def wiki_anchor_tag(self) -> str:
        return "email"

    @override
    def get_template_values(self) -> dict[str, Any]:
        return {"items": self.items}

    @override
    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return lowercase_text.startswith("question #") or all(s in lowercase_text for s in ["your", "question", "mail"])

    @override
    def get_start_time(self, transcript: DiarizedTranscript) -> float | None:
        for chunk in transcript:
            if "mail" in chunk["text"].lower() and chunk["speaker"] == "Steve":
                return chunk["start"]

        return None

    @override
    @staticmethod
    def from_show_notes(segment_data: list[Tag]) -> "EmailSegment":
        text = segment_data[0].text
        if ": " not in text:
            return EmailSegment(items=[])

        raw_items = text.split(":")[1].split(",")
        items = [raw_item.strip() for raw_item in raw_items]
        return EmailSegment(items=items)

    @override
    @staticmethod
    def from_lyrics(text: str) -> "EmailSegment":
        lines = [*[line.strip() for line in text.split("\n") if line.strip()][1:], None]  # sentinel value

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
    description: str = "N/A<!-- Failed to extract description -->"

    title: str = "Forgotten Superheroes of Science"

    @property
    @override
    def template_name(self) -> str:
        raise NotImplementedError

    @property
    @override
    def llm_prompt(self) -> str:
        return "Please identify the start of the 'forgotten superheroes of science' segment."

    @property
    @override
    def wiki_anchor_tag(self) -> str:
        return "fss"

    @override
    def get_template_values(self) -> dict[str, Any]:
        raise NotImplementedError

    @override
    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        first_format = bool(re.match(r"forgotten superhero(es)? of science", lowercase_text))
        second_format = bool(re.match(r"fsos", lowercase_text))
        return first_format or second_format

    @override
    @override
    def get_start_time(self, transcript: DiarizedTranscript) -> float | None:
        for chunk in transcript:
            if are_strings_in_string(["forgotten", "hero", "science"], chunk["text"].lower()):
                return chunk["start"]

        return None

    @override
    @staticmethod
    def from_summary_text(text: str) -> "ForgottenSuperheroesOfScienceSegment":
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        lines += [""] * (1 - len(lines))
        subject, *_ = lines

        return ForgottenSuperheroesOfScienceSegment(subject=subject)

    @override
    @staticmethod
    def from_lyrics(text: str) -> "ForgottenSuperheroesOfScienceSegment":
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        lines += [""] * (2 - len(lines))
        _segment_name, subject, *extra = lines

        if extra:
            logger.warning(f"Unexpected extra lines in dumbest thing of the week segment: {extra}")

        return ForgottenSuperheroesOfScienceSegment(
            subject=subject,
        )


@dataclass(kw_only=True)
class InterviewSegment(FromLyricsSegment, FromShowNotesSegment):
    name: str
    url: str

    @property
    @override
    def template_name(self) -> str:
        return "interview"

    @property
    @override
    def llm_prompt(self) -> str:
        return f"Please identity the beginning of the interview with {self.name}."

    @property
    @override
    def wiki_anchor_tag(self) -> str:
        return "interview"

    @override
    def get_template_values(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "url": self.url,
        }

    @override
    def get_start_time(self, transcript: DiarizedTranscript) -> float | None:
        for chunk in transcript:
            if are_strings_in_string(["go", "to", "interview"], chunk["text"].lower()):
                return chunk["start"]

        return None

    @override
    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return lowercase_text.startswith("interview with")

    @override
    @staticmethod
    def from_show_notes(segment_data: list[Tag]) -> "InterviewSegment":
        text = segment_data[0].text
        name = re.split(r"[w|W]ith", text)[1]

        return InterviewSegment(name=name.strip(":- "), url="")

    @override
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
class IntroSegment(BaseSegment):
    """The segment that introduces the show and has banter betweeen the rogues."""

    @property
    @override
    def template_name(self) -> str:
        return "intro"

    @property
    @override
    def llm_prompt(self) -> str:
        raise NotImplementedError

    @property
    @override
    def wiki_anchor_tag(self) -> str:
        return "intro"

    @override
    def get_template_values(self) -> dict[str, Any]:
        return {}

    @override
    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        raise NotImplementedError

    @override
    def get_start_time(self, transcript: DiarizedTranscript) -> float | None:
        del transcript
        return 0.0


@dataclass(kw_only=True)
class LogicalFallacySegment(FromLyricsSegment, NonNewsSegmentMixin):
    topic: str

    title: str = "Name That Logical Fallacy"

    @property
    @override
    def template_name(self) -> str:
        return "logical_fallacy"

    @property
    @override
    def llm_prompt(self) -> str:
        return "Please identify the start of the 'name that logical fallacy' segment."

    @property
    @override
    def wiki_anchor_tag(self) -> str:
        return "ntlf"

    @override
    def get_template_values(self) -> dict[str, Any]:
        return {"topic": self.topic}

    @override
    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return "name that logical fallacy" in lowercase_text

    @override
    def get_start_time(self, transcript: DiarizedTranscript) -> float | None:
        for chunk in transcript:
            if are_strings_in_string(["name", "logical", "fallacy"], chunk["text"].lower()):
                return chunk["start"]

        return None

    @override
    @staticmethod
    def from_lyrics(text: str) -> "LogicalFallacySegment":
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        lines += [""] * (2 - len(lines))
        _segment_name, *topic = lines

        return LogicalFallacySegment(topic=" ".join(topic))


@dataclass(kw_only=True)
class NoisySegment(FromLyricsSegment, FromShowNotesSegment):
    valid_splitters: ClassVar[str] = ":-"

    last_week_answer: str = "<!-- Failed to extract last week's answer -->"

    @property
    @override
    def template_name(self) -> str:
        return "noisy"

    @property
    @override
    def llm_prompt(self) -> str:
        return "Please identify the start of the 'who's that noisy' segment."

    @property
    @override
    def wiki_anchor_tag(self) -> str:
        return "wtn"

    @override
    def get_template_values(self) -> dict[str, Any]:
        return {"last_week_answer": self.last_week_answer}

    @override
    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return bool(re.search(r"who.s that noisy", lowercase_text))

    @override
    def get_start_time(self, transcript: DiarizedTranscript) -> float | None:
        for chunk in transcript:
            if are_strings_in_string(["who", "that", "noisy"], chunk["text"].lower()):
                return chunk["start"]

        return None

    @override
    @staticmethod
    def from_show_notes(segment_data: list[Tag]) -> "NoisySegment":
        """Create a NoisySegment that will be merged with the lyrics segment."""
        if len(segment_data) == 1:
            return NoisySegment()

        for splitter in NoisySegment.valid_splitters:
            if splitter in segment_data[1].text:
                return NoisySegment(
                    last_week_answer=segment_data[1].text.split(splitter)[1].strip(),
                )

        return NoisySegment()

    @override
    @staticmethod
    def from_lyrics(text: str) -> "NoisySegment":
        del text
        return NoisySegment()


@dataclass(kw_only=True)
class OutroSegment(BaseSegment):
    @property
    @override
    def template_name(self) -> str:
        return "outro"

    @property
    @override
    def llm_prompt(self) -> str:
        return "Please find the start of the outro. This is typically where Steve says 'Skeptics' Guide to the Universe is produced by SGU Productions'"

    @property
    @override
    def wiki_anchor_tag(self) -> str:
        return "outro"

    @override
    def get_template_values(self) -> dict[str, Any]:
        return {}

    @override
    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        raise NotImplementedError

    @override
    def get_start_time(self, transcript: DiarizedTranscript) -> float | None:
        for chunk in transcript:
            if are_strings_in_string(
                ["skeptic", "guide", "to", "the", "universe", "produced", "by", "sgu", "productions"],
                chunk["text"].lower(),
            ):
                return chunk["start"]

        return None


@dataclass(kw_only=True)
class QuickieSegment(FromLyricsSegment, NonNewsSegmentMixin):
    title: str
    subject: str
    url: str

    @property
    @override
    def template_name(self) -> str:
        return "quickie"

    @property
    @override
    def llm_prompt(self) -> str:
        return f"Please find the start of the 'quickie' segment: {self.title}. The subject is: {self.subject}"

    @property
    @override
    def wiki_anchor_tag(self) -> str:
        return "quickie"

    @override
    def get_template_values(self) -> dict[str, Any]:
        article_publication = None
        article_title = None

        if self.url:
            article_publication = urlparse(self.url).netloc
            article_title = get_article_title(self.url) or self.url

        return {
            "title": self.title,
            "subject": self.subject,
            "url": self.url,
            "article_title": article_title,
            "article_publication": article_publication,
        }

    @override
    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return lowercase_text.startswith("quickie with")

    @override
    def get_start_time(self, transcript: DiarizedTranscript) -> float | None:
        for chunk in transcript:
            if are_strings_in_string(["quickie", "with"], chunk["text"].lower()):
                return chunk["start"]

            if are_strings_in_string(self.subject.split(), chunk["text"].lower()):
                return chunk["start"]

        return None

    @override
    @staticmethod
    def from_lyrics(text: str) -> "QuickieSegment":
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        lines += [""] * (3 - len(lines))
        title, subject, url, *extra = lines

        if extra:
            logger.warning(f"Unexpected extra lines in quickie segment: {extra}")

        return QuickieSegment(
            title=title,
            subject=subject,
            url=url,
        )


@dataclass(kw_only=True)
class QuoteSegment(FromLyricsSegment):
    quote: str
    attribution: str

    @property
    @override
    def template_name(self) -> str:
        return "quote"

    @property
    @override
    def llm_prompt(self) -> str:
        return "Please identify the start of the 'quote' segment. This is usually Steve asking Evan for the quote."

    @property
    @override
    def wiki_anchor_tag(self) -> str:
        return "qow"

    @override
    def get_template_values(self) -> dict[str, Any]:
        return {"quote": self.quote, "attribution": self.attribution}

    @override
    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return lowercase_text.startswith("skeptical quote of the week")

    @override
    def get_start_time(self, transcript: DiarizedTranscript) -> float | None:
        for chunk in transcript:
            text = chunk["text"].lower()
            if "quote" in text and chunk["speaker"] == "Steve":
                return chunk["start"]

        return None

    @override
    @staticmethod
    def from_lyrics(text: str) -> "QuoteSegment":
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        lines += [""] * (3 - len(lines))
        _segment_name, *quote_parts, attribution = lines

        if not quote_parts:
            logger.warning("Unable to extract quote attribution from lyrics.")

        return QuoteSegment(quote=" ".join(quote_parts), attribution=attribution)


@dataclass(kw_only=True)
class SwindlersListSegment(FromLyricsSegment, FromSummaryTextSegment, NonNewsSegmentMixin):
    topic: str = "N/A<!-- Failed to extract topic -->"
    url: str | None

    title: str = "Swindler's List"

    @property
    @override
    def template_name(self) -> str:
        raise NotImplementedError

    @property
    @override
    def llm_prompt(self) -> str:
        raise NotImplementedError

    @property
    @override
    def wiki_anchor_tag(self) -> str:
        return "swindlers"

    @override
    def get_template_values(self) -> dict[str, Any]:
        article_publication = None
        article_title = None
        if self.url:
            article_publication = urlparse(self.url).netloc
            article_title = get_article_title(self.url) or self.url

        return {
            "topic": self.topic,
            "url": self.url,
            "article_title": article_title,
            "article_publication": article_publication,
        }

    @override
    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return bool(re.match(r"swindler.s list", lowercase_text))

    @override
    def get_start_time(self, transcript: DiarizedTranscript) -> float | None:
        for chunk in transcript:
            if are_strings_in_string(["swindler", "list"], chunk["text"].lower()):
                return chunk["start"]

        return None

    @override
    @staticmethod
    def from_summary_text(text: str) -> "SwindlersListSegment":
        topic = text.split(":")[1].strip()
        return SwindlersListSegment(topic=topic, url=None)

    @override
    @staticmethod
    def from_lyrics(text: str) -> "SwindlersListSegment":
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        lines += [""] * (3 - len(lines))
        _segment_name, topic, url, *extra = lines

        if extra:
            logger.warning(f"Unexpected extra lines in dumbest thing of the week segment: {extra}")

        return SwindlersListSegment(topic=topic, url=url)


@dataclass(kw_only=True)
class TikTokSegment(FromLyricsSegment):
    title: str
    url: str

    @property
    @override
    def template_name(self) -> str:
        return "tiktok"

    @property
    @override
    def llm_prompt(self) -> str:
        return f"Please identify the start of the 'from tiktok' segment. The topic is: {self.title}"

    @property
    @override
    def wiki_anchor_tag(self) -> str:
        return "tiktok"

    @override
    def get_template_values(self) -> dict[str, Any]:
        return {"title": self.title, "url": self.url}

    @override
    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return lowercase_text.startswith("from tiktok")

    @override
    def get_start_time(self, transcript: DiarizedTranscript) -> float | None:
        for chunk in transcript:
            if are_strings_in_string(self.title.split(), chunk["text"].lower()):
                return chunk["start"]

        return None

    @override
    @staticmethod
    def from_lyrics(text: str) -> "TikTokSegment":
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        lines += [""] * (3 - len(lines))
        _segment_name, title, url, *extra = lines

        if extra:
            logger.warning(f"Unexpected extra lines in tiktok segment: {extra}")

        if not title:
            raise StringMatchError(f"Failed to extract title from: {text}")

        if not url or not string_is_url(url):
            logger.error(f"Failed to extract valid URL from: {text}")

        return TikTokSegment(title=title, url=url)


@dataclass(kw_only=True)
class UnknownSegment(BaseSegment):
    """A segment that could not be identified."""

    title: str
    extra_text: str
    url: str | None

    @property
    @override
    def template_name(self) -> str:
        return "unknown"

    @property
    @override
    def llm_prompt(self) -> str:
        return f"Please identify the start of the segment whose title is: {self.title}, {self.extra_text}"

    @property
    @override
    def wiki_anchor_tag(self) -> str:
        return "unknown"

    @override
    def get_template_values(self) -> dict[str, Any]:
        return {"title": self.title, "extra_text": self.extra_text, "url": self.url}

    @override
    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        raise NotImplementedError

    @override
    def get_start_time(self, transcript: DiarizedTranscript) -> float | None:
        for chunk in transcript:
            if are_strings_in_string(self.title.split(), chunk["text"].lower()):
                return chunk["start"]

            if are_strings_in_string(self.extra_text.split(), chunk["text"].lower()):
                return chunk["start"]

        return None

    @staticmethod
    def create(text: str) -> "UnknownSegment":
        """Create an UnknownSegment from a string."""
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
class WhatsTheWordSegment(FromLyricsSegment, NonNewsSegmentMixin):
    word: str

    title: str = "What's the Word?"

    @property
    @override
    def template_name(self) -> str:
        return "whats_the_word"

    @property
    @override
    def llm_prompt(self) -> str:
        return (
            "Please find the start of the 'what's the word' segment."
            + "This is typically introduced by Steve asking Cara for the word."
        )

    @property
    @override
    def wiki_anchor_tag(self) -> str:
        return "wtw"

    @override
    def get_template_values(self) -> dict[str, Any]:
        return {"word": self.word}

    @override
    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return bool(re.match(r"what.s the word", lowercase_text))

    @override
    def get_start_time(self, transcript: DiarizedTranscript) -> float | None:
        for chunk in transcript:
            if re.match(r"what.?s the word", chunk["text"].lower()):
                return chunk["start"]

            if self.word.lower() in chunk["text"].lower():
                return chunk["start"]

        return None

    @override
    @staticmethod
    def from_lyrics(text: str) -> "WhatsTheWordSegment":
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        lines += [""] * (2 - len(lines))
        _segment_name, word, *extra = lines

        if extra:
            logger.warning(f"Unexpected extra lines in whatstheword segment: {extra}")

        if not word:
            raise StringMatchError(f"Failed to extract title from: {text}")

        return WhatsTheWordSegment(word=word)
