"""Models only using built-in types and from the standard library."""

from enum import Enum
from typing import TypedDict


class EpisodeStatus(Enum):
    """Possible statuses of an episode transcript."""

    UNKNOWN = ""
    OPEN = "open"
    MACHINE = "machine"
    BOT = "bot"
    INCOMPLETE = "incomplete"
    PROOFREAD = "proofread"
    VERIFIED = "verified"


class DiarizedTranscriptChunk(TypedDict):
    """A chunk of a diarized transcript.

    Attributes:
        start: The start time of the chunk.
        end: The end time of the chunk.
        text: The text content of the chunk.
        speaker: The speaker associated with the chunk.
    """

    start: float
    end: float
    text: str
    speaker: str


class TranscriptSegment(TypedDict):
    """Segment of a transcript."""

    start: float
    end: float
    text: str


class PhraseInfo(TypedDict):
    """Information about a phrase."""

    display: str


class RecognizedPhrase(TypedDict):
    """Information about a recognized phrase."""

    offsetInTicks: float
    durationInTicks: float
    nBest: list[PhraseInfo]


DiarizedTranscript = list[DiarizedTranscriptChunk]
RawTranscript = list[TranscriptSegment]
