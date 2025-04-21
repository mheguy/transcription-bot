import re
from typing import Any, override
from urllib.parse import urlparse

from bs4 import Tag
from loguru import logger
from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

from transcription_bot.models.episode_segments.base import FromLyricsSegment, FromShowNotesSegment
from transcription_bot.models.simple_models import DiarizedTranscript
from transcription_bot.utils.exceptions import StringMatchError
from transcription_bot.utils.helpers import find_single_element, get_article_title
from transcription_bot.utils.issue_tracking import report_issue


@dataclass(kw_only=True)
class ScienceOrFictionItem:
    """An item in the science or fiction segment."""

    number: int
    name: str
    article_url: str | None
    sof_result: str

    article_title: str | None
    article_publication: str | None


@dataclass
class RogueGuess:
    """A rogue's guess in the science or fiction segment."""

    num: int
    name: str
    answer: ScienceOrFictionItem


@dataclass(kw_only=True)
class ScienceOrFictionMetadata:
    """Metadata for the science or fiction segment."""

    rogues: list[RogueGuess]
    host: str
    sweep: str = ""
    swept: str = ""
    win: str = ""
    clever: str = ""


@dataclass(kw_only=True)
class ScienceOrFictionLlmData:
    """Information about how the rogues guessed.

    All lists are in chronological order.

    guess_timestamps: The timestamps where the host asked the rogues to guess.
    rogues: The names of the rogues that guessed (in the order they guessed).
    rogue_answers: Each rogue's selected item number.
    host: The name of the host (usually Steve).
    order_of_reveal: The order in which the host revealed the answers.
    reveal_timestamps: The timestamps where the host explained each answer.
    """

    guess_timestamps: list[float]  # TODO: Use this to split up the segment
    rogues: list[str]
    rogue_answers: list[int]
    host: str
    order_of_reveal: list[int]  # TODO: Use this to split up the segment
    reveal_timestamps: list[float]  # TODO: Use this to split up the segment


_MISSING_FICTION_ITEM_IN_SCIENCE_OR_FICTION_MESSAGE = """
Unfortunately, this episode did not have a 'fiction' item listed in the show notes on the website.
Consequently, the Science of Fiction data needs to be manually corrected.

I first saw this issue in episode 1018 and I contacted info@theskepticsguide.com.
They did not respond, which was disappointing as it is an issue that should be fixed on their end.
Rather than have the bot generate no transcript at all, instead I added this message in the hopes that the human editor
will see this and fix it. If you're reading this: please contact the podcast creators to ask them to fix this issue.
"""


def _create_science_or_fiction_metadata(
    llm_data: ScienceOrFictionLlmData | None, items: list[ScienceOrFictionItem]
) -> ScienceOrFictionMetadata:
    if llm_data is None:
        raise ValueError("Segment has no metadata")

    fiction_item = next((item for item in items if item.sof_result.lower() == "fiction"), None)

    if fiction_item:
        correct_answer = fiction_item.number
    else:
        correct_answer = 0
        report_issue(_MISSING_FICTION_ITEM_IN_SCIENCE_OR_FICTION_MESSAGE)

    guessed_items = set(llm_data.rogue_answers)
    item_map = {item.number: item for item in items}

    rogue_answer_map = dict(zip(llm_data.rogues, llm_data.rogue_answers, strict=True))

    rogues: list[RogueGuess] = []
    for num, (rogue_name, answer_num) in enumerate(rogue_answer_map.items(), start=1):
        rogues.append(RogueGuess(num=num, name=rogue_name, answer=item_map[answer_num]))

    result_data = ScienceOrFictionMetadata(rogues=rogues, host=llm_data.host)

    # No rogue guessed the correct answer.
    all_guesses_incorrect = all(correct_answer != guess for guess in guessed_items)
    if all_guesses_incorrect:
        result_data.sweep = "y"
        return result_data

    # All rogues guessed right
    all_guesses_correct = all(correct_answer == guess for guess in guessed_items)
    if all_guesses_correct:
        result_data.swept = "y"
        return result_data

    # All items were guessed at least once.
    all_items_guessed = guessed_items == {item.number for item in items}
    if all_items_guessed:
        result_data.clever = "y"
        return result_data

    # At least one Rogue guessed wrong, but not all.
    if not all_guesses_correct and not all_guesses_incorrect:
        result_data.win = "y"
        return result_data

    logger.error("SoF results did not fit into a category.")
    return result_data


@dataclass(kw_only=True, config=ConfigDict(arbitrary_types_allowed=True))
class ScienceOrFictionSegment(FromLyricsSegment, FromShowNotesSegment):
    """A segment where the host asks the rogues to guess if something is science or fiction."""

    raw_items: list[Tag]
    theme: str | None = None
    metadata: ScienceOrFictionLlmData | None = None

    @property
    @override
    def template_name(self) -> str:
        return "science_or_fiction"

    @property
    @override
    def llm_prompt(self) -> str:
        return "Please identify the start of the 'science or fiction' segment."

    @property
    @override
    def wiki_anchor_tag(self) -> str:
        return "theme"

    @override
    def get_template_values(self) -> dict[str, Any]:
        items = ScienceOrFictionSegment._process_raw_items(self.raw_items)

        metadata = _create_science_or_fiction_metadata(self.metadata, items)

        return {
            "items": items,
            "theme": self.theme,
            "metadata": metadata,
        }

    @override
    @staticmethod
    def match_string(lowercase_text: str) -> bool:
        return "science or fiction" in lowercase_text

    @override
    def get_start_time(self, transcript: DiarizedTranscript) -> float | None:
        for chunk in transcript:
            if "time for science or fiction" in chunk["text"].lower():
                return chunk["start"]

        return None

    @override
    @staticmethod
    def from_show_notes(segment_data: list[Tag]) -> "ScienceOrFictionSegment":
        raw_items = [i for i in segment_data[1].children if isinstance(i, Tag)]
        return ScienceOrFictionSegment(raw_items=raw_items)

    @staticmethod
    def _process_raw_items(raw_items: list[Tag]) -> list[ScienceOrFictionItem]:
        items: list[ScienceOrFictionItem] = []

        science_items = 1
        for raw_item in raw_items:
            title_text = find_single_element(raw_item, "span", "science-fiction__item-title").text
            match = re.search(r"(\d+)", title_text)
            if not match:
                raise StringMatchError(f"Failed to extract item number from: {title_text}")

            item_number = int(match.group(1))

            p_tag = find_single_element(raw_item, "p", None)
            p_text = p_tag.text.strip()

            if better_tag := p_tag.next:
                p_text = better_tag.text.strip()

            answer = find_single_element(raw_item, "span", "quiz__answer").text

            try:
                a_tag = find_single_element(p_tag, "a", None)
                article_url = a_tag.get("href", "")
                if not isinstance(article_url, str):
                    raise TypeError("Got an unexpected type in url")
            except ValueError:
                article_url = ""

            publication = None
            article_title = None
            if article_url:
                publication = urlparse(article_url).netloc
                article_title = get_article_title(article_url) or article_url

            if answer.lower() == "science":
                sof_result = f"science{science_items}"
                science_items += 1
            else:
                sof_result = "fiction"

            items.append(
                ScienceOrFictionItem(
                    number=item_number,
                    name=p_text,
                    article_url=article_url,
                    sof_result=sof_result,
                    article_publication=publication,
                    article_title=article_title,
                )
            )

        return items

    @override
    @staticmethod
    def from_lyrics(text: str) -> "ScienceOrFictionSegment":
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        theme = None

        for line in lines:
            if line.lower().startswith("theme:"):
                theme = line.split(":")[1].strip()
                break

        return ScienceOrFictionSegment(raw_items=[], theme=theme)
