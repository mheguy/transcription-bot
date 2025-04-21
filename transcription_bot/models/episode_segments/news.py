import re
from typing import Any, override
from urllib.parse import urlparse

from pydantic.dataclasses import dataclass

from transcription_bot.models.episode_segments.base import BaseSegment, FromLyricsSegment
from transcription_bot.models.simple_models import DiarizedTranscript
from transcription_bot.utils.exceptions import StringMatchError
from transcription_bot.utils.helpers import get_article_title, string_is_url


@dataclass(kw_only=True)
class NewsItem(BaseSegment):
    item_number: int
    topic: str
    url: str | None

    @property
    @override
    def template_name(self) -> str:
        return "news"

    @property
    @override
    def llm_prompt(self) -> str:
        return f"Please identify the start of the news segment whose topic is: {self.topic}"

    @property
    @override
    def wiki_anchor_tag(self) -> str:
        return "news_item"

    @override
    def get_template_values(self) -> dict[str, Any]:
        article_publication = None
        article_title = None
        if self.url:
            article_publication = urlparse(self.url).netloc
            article_title = get_article_title(self.url) or self.url

        return {
            "item_number": self.item_number,
            "topic": self.topic,
            "url": self.url,
            "article_title": article_title,
            "article_publication": article_publication,
        }

    @override
    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        raise NotImplementedError

    @override
    def get_start_time(self, transcript: DiarizedTranscript) -> float | None:
        del transcript

        return None


@dataclass(kw_only=True)
class NewsMetaSegment(FromLyricsSegment):
    """This "metasegment" contains multiple news segments."""

    news_segments: list[NewsItem]

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
        return "news_meta"

    @override
    def get_template_values(self) -> dict[str, Any]:
        raise NotImplementedError

    @override
    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return lowercase_text.startswith("news item")

    @override
    def get_start_time(self, transcript: DiarizedTranscript) -> float | None:
        raise NotImplementedError

    @override
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

                match = re.match(r"news items? ?[#$]?\d+\s*.\s*(.+)", line, re.IGNORECASE)
                if not match:
                    raise StringMatchError(f"Failed to extract news topic from: {line}")
                topic = match.group(1).strip()

                items.append(NewsItem(item_number=item_counter, topic=topic, url=url))

        return NewsMetaSegment(news_segments=items)
