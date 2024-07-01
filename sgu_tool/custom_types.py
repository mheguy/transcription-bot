from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from pyannote.core.utils.types import Label


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


class DiarizedTranscriptSegment(TypedDict):
    start_time: str
    end_time: str
    speaker: "str | Label"
    text: str


class DiarizedTranscript(TypedDict):
    rogues: list[str]
    segments: list[DiarizedTranscriptSegment]
