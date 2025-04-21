import math
from abc import ABC, abstractmethod
from dataclasses import field
from typing import Any

from bs4 import Tag
from pydantic.dataclasses import dataclass

from transcription_bot.models.simple_models import DiarizedTranscript


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
        """Get the start time of the segment (or None in the case of failure)."""

    @property
    def duration(self) -> float:
        """Provide the duration of the segment in minutes."""
        if self.start_time is None:
            return 0

        return (self.end_time - self.start_time) / 60


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
    def from_show_notes(segment_data: list[Tag]) -> "FromShowNotesSegment":
        """Create a segment from the show notes."""


class FromLyricsSegment(BaseSegment, ABC):
    """A segment whose source is the embedded lyrics."""

    @staticmethod
    @abstractmethod
    def from_lyrics(text: str) -> "FromLyricsSegment":
        """Create a segment from the embedded lyrics."""
        raise NotImplementedError
