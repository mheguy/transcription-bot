import itertools
from enum import Enum
from time import struct_time
from typing import Any, ClassVar, TypedDict

from mwparserfromhell.nodes import Template
from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

_DEFAULT_SORTING_VALUE = "zzz"


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
    _REQUIRED_PROPS: ClassVar[tuple[str, ...]] = ("episode", "date", "status")
    _SORT_PARAM_MAPPING: ClassVar[dict[str, str]] = {
        "other": "sort_other",
        "theme": "sort_theme",
        "interviewee": "sort_interviewee",
        "rogue": "sort_rogue",
    }
    _OPTIONAL_PROPS: ClassVar[tuple[str, ...]] = tuple(
        itertools.chain(_SORT_PARAM_MAPPING.keys(), _SORT_PARAM_MAPPING.values())
    )

    episode: str
    date: str
    status: EpisodeStatus

    other: str | None = None
    sort_other: str | None = None
    theme: str | None = None
    sort_theme: str | None = None
    interviewee: str | None = None
    sort_interviewee: str | None = None
    rogue: str | None = None
    sort_rogue: str | None = None

    def __or__(self, other: Any) -> "SguListEntry":
        """Combine two entries together.

        When combining, the second will overwrite falsey values in the first.
        """
        if not isinstance(other, SguListEntry):
            return self

        return SguListEntry(
            episode=self.episode,
            date=self.date,
            status=self.status,
            other=self.other or other.other,
            sort_other=self.sort_other or other.sort_other,
            theme=self.theme or other.theme,
            sort_theme=self.sort_theme or other.sort_theme,
            interviewee=self.interviewee or other.interviewee,
            sort_interviewee=self.sort_interviewee or other.sort_interviewee,
            rogue=self.rogue or other.rogue,
            sort_rogue=self.sort_rogue or other.sort_rogue,
        )

    @staticmethod
    def from_template(template: Template) -> "SguListEntry":
        """Construct an episode list entry from a template."""
        return SguListEntry(
            episode=template.get("episode").value.strip_code().strip(),
            date=template.get("date").value.strip_code().strip(),
            status=EpisodeStatus(template.get("status").value.strip_code().strip()),
            **SguListEntry._get_optional_params_from_template(template),
        )

    @staticmethod
    def safely_get_param_value(template: Template, key: str) -> str | None:
        """Get a param value from a template, or return None if it doesn't exist."""
        result = template.get(key, None)

        if result is None:
            return None

        return result.value.strip()

    @staticmethod
    def _get_optional_params_from_template(template: Template) -> dict[str, str]:
        optionals = {}
        for param in SguListEntry._OPTIONAL_PROPS:
            if value := SguListEntry.safely_get_param_value(template, param):
                optionals[param] = value

        return optionals

    def to_dict(self) -> dict[str, str]:
        """Return a dictionary representation of the object."""
        dict_representation = {required: getattr(self, required) for required in self._REQUIRED_PROPS}
        dict_representation["status"] = self.status.value

        for key, sort_key in self._SORT_PARAM_MAPPING.items():
            value: str = getattr(self, key)
            dict_representation[key] = value

            if not value or value.lower() == "n":
                dict_representation[sort_key] = _DEFAULT_SORTING_VALUE
            else:
                dict_representation[sort_key] = ""

        return dict_representation

    def update_template(self, template: Template) -> None:
        """Modify a template to match the current object."""
        for k, v in self.to_dict().items():
            template.add(k, v)


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


@dataclass(config=ConfigDict(arbitrary_types_allowed=True))
class PodcastRssEntry:
    """Basic information about a podcast episode."""

    episode_number: int
    official_title: str
    summary: str
    download_url: str
    episode_url: str
    published_time: struct_time


@dataclass
class EpisodeData:
    """Detailed data about a podcast episode.

    Attributes:
        podcast: The basic information about the episode.
        lyrics: The lyrics that were embedded in the MP3 file.
        show_notes: The show notes of the episode from the website.
    """

    podcast: PodcastRssEntry
    lyrics: str
    show_notes: bytes


DiarizedTranscript = list[DiarizedTranscriptChunk]
