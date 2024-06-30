from typing import TypedDict


class PodcastFeedEntryLink(TypedDict):
    """Only the fields we use."""

    length: str
    href: str


class PodcastFeedEntry(TypedDict):
    """Only the fields we use."""

    title: str
    link: str
    links: list[PodcastFeedEntryLink]


class TranscriptionSegment(TypedDict):
    start_time: float
    end_time: float
    text: str


class Transcription(TypedDict):
    text: str
    segments: list[TranscriptionSegment]
