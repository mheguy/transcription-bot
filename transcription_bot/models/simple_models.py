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
        start (float): The start time of the chunk.
        end (float): The end time of the chunk.
        text (str): The text content of the chunk.
        speaker (str): The speaker associated with the chunk.
    """

    start: float
    end: float
    text: str
    speaker: str


DiarizedTranscript = list[DiarizedTranscriptChunk]
