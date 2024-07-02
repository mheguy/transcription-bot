from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sgu.hosts import Host


def get_segments(podcast_summary: str) -> list["BaseSegment"]:
    return [create_segment_from_text(line) for line in podcast_summary.split(";")]


def create_segment_from_text(text: str) -> "BaseSegment":
    if text.startswith("Quickie with "):
        return QuickieSegment(text)

    if text.startswith("News Items: "):
        return NewsSegment(text)

    if text.startswith("Your Questions and E-mails: "):
        return EmailSegment(text)

    if text == "Who's That Noisy":
        return NoisySegment()

    if text == "Science or Fiction":
        return ScienceOrFictionSegment()

    return UnknownSegment(text)


@dataclass
class NewsItem:
    topic: str

    host: "Host | None" = None


class BaseSegment(ABC):
    @property
    @abstractmethod
    def summary(self) -> str:
        raise NotImplementedError


@dataclass
class UnknownSegment(BaseSegment):
    _summary: str

    @property
    def summary(self) -> str:
        return self._summary


class QuickieSegment(BaseSegment):
    def __init__(self, summary: str) -> None:
        self._summary = summary

    @property
    def summary(self) -> str:
        return self._summary


class NewsSegment(BaseSegment):
    def __init__(self, summary: str) -> None:
        self._summary = summary

    @property
    def summary(self) -> str:
        return self._summary


class EmailSegment(BaseSegment):
    def __init__(self, summary: str) -> None:
        self._summary = summary

    @property
    def summary(self) -> str:
        return self._summary


class NoisySegment(BaseSegment):
    @property
    def summary(self) -> str:
        return "Who's That Noisy"


class ScienceOrFictionSegment(BaseSegment):
    @property
    def summary(self) -> str:
        return "Science or Fiction"
