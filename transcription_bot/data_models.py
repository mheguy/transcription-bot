from enum import Enum
from typing import ClassVar

from pydantic.dataclasses import dataclass


class EpisodeStatus(Enum):
    """Possible statuses of an episode transcript."""

    UNKNOWN = ""
    OPEN = "open"
    MACHINE = "machine"
    BOT = "bot"
    INCOMPLETE = "incomplete"
    PROOFREAD = "proofread"
    VERIFIED = "verified"


@dataclass
class SguListEntry:
    """Data required by the SGU list entry template.

    date: MM-DD format.
    """

    identifier: ClassVar[str] = "SGU list entry"

    episode: int
    date: str
    status: EpisodeStatus
    other: str = "N"
    sort_other: str = "zzz"
    theme: str = "N"
    sort_theme: str = "zzz"
    interviewee: str = "N"
    sort_interviewee: str = "zzz"
    rogue: str = "N"
    sort_rogue: str = "zzz"
