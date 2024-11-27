from dataclasses import asdict
from enum import Enum
from typing import TYPE_CHECKING, ClassVar

from pydantic.dataclasses import dataclass

if TYPE_CHECKING:
    from mwparserfromhell.nodes import Template


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

    episode: str
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

    @staticmethod
    def from_template(template: "Template") -> "SguListEntry":
        """Construct an episode list entry from a template."""
        return SguListEntry(
            episode=template.get("episode").value.strip_code().strip(),
            date=template.get("date").value.strip_code().strip(),
            status=EpisodeStatus(template.get("status").value.strip_code().strip()),
            other=template.get("other").value.strip_code().strip(),
            sort_other=template.get("sort_other").value.strip_code().strip(),
            theme=template.get("theme").value.strip_code().strip(),
            sort_theme=template.get("sort_theme").value.strip_code().strip(),
            interviewee=template.get("interviewee").value.strip_code().strip(),
            sort_interviewee=template.get("sort_interviewee").value.strip_code().strip(),
            rogue=template.get("rogue").value.strip_code().strip(),
            sort_rogue=template.get("sort_rogue").value.strip_code().strip(),
        )

    def to_dict(self) -> dict[str, str]:
        """Return a dictionary representation of the object."""
        literal_dict = asdict(self)
        literal_dict["status"] = self.status.value
        return literal_dict

    def update_template(self, template: "Template") -> None:
        """Modify a template to match the current object."""
        template.add("episode", self.episode)
        template.add("date", self.date)
        template.add("status", self.status.value)
        template.add("other", self.other)
        template.add("sort_other", self.sort_other)
        template.add("theme", self.theme)
        template.add("sort_theme", self.sort_theme)
        template.add("interviewee", self.interviewee)
        template.add("sort_interviewee", self.sort_interviewee)
        template.add("rogue", self.rogue)
        template.add("sort_rogue", self.sort_rogue)
