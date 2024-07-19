from typing import TYPE_CHECKING, TypeVar

from sgu.custom_logger import logger
from sgu.segment_types import BaseSegment, NoisySegment, ScienceOrFictionSegment

if TYPE_CHECKING:
    from sgu.segment_types import Segments


T = TypeVar("T", bound=BaseSegment)


def join_segments(
    lyric_segments: "Segments",
    show_note_segments: "Segments",
    summary_text_segments: "Segments",
) -> "Segments":
    """Decide which segments to keep and flag any potential issues."""
    find_duplicates(lyric_segments, show_note_segments, summary_text_segments)

    merge_noisy_segments(lyric_segments, show_note_segments)
    merge_science_or_fiction_segments(lyric_segments, show_note_segments)

    return lyric_segments


def merge_noisy_segments(lyric_segments: "Segments", show_note_segments: "Segments") -> None:
    lyric_segment = get_segment_of_type(NoisySegment, lyric_segments)
    show_note_segment = get_segment_of_type(NoisySegment, show_note_segments)
    if lyric_segment and show_note_segment:
        lyric_segment.last_week_answer = show_note_segment.last_week_answer


def merge_science_or_fiction_segments(lyric_segments: "Segments", show_note_segments: "Segments") -> None:
    lyric_segment = get_segment_of_type(ScienceOrFictionSegment, lyric_segments)
    show_note_segment = get_segment_of_type(ScienceOrFictionSegment, show_note_segments)
    if lyric_segment and show_note_segment:
        lyric_segment.items = show_note_segment.items


def get_segment_of_type(segment_type: type[T], segments: "Segments") -> "T | None":
    for segment in segments:
        if isinstance(segment, segment_type):
            return segment

    return None


def find_duplicates(*segment_collections: "Segments") -> None:
    for segment_collection in segment_collections:
        seen = []

        for segment in segment_collection:
            if segment in seen:
                logger.info("Found duplicate segment: %s", segment)
