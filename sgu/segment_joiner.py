from typing import TYPE_CHECKING, TypeVar

from sgu.custom_logger import logger
from sgu.episode_segments import BaseSegment, NewsMetaSegment, NoisySegment, ScienceOrFictionSegment

if TYPE_CHECKING:
    from sgu.episode_segments import Segments


T = TypeVar("T", bound=BaseSegment)


def join_segments(
    lyric_segments: "Segments",
    show_note_segments: "Segments",
    summary_text_segments: "Segments",
) -> "Segments":
    """Join segments from different collections and flag any potential issues.

    NOTE: This modifies the elements of the `lyric_segments` collection in place.
    """
    _find_duplicate_segments(lyric_segments, show_note_segments, summary_text_segments)

    segments = _flatten_news(lyric_segments)

    _merge_noisy_segments(segments, show_note_segments)
    _merge_science_or_fiction_segments(segments, show_note_segments)

    return segments


def _find_duplicate_segments(*segment_collections: "Segments") -> None:
    for segment_collection in segment_collections:
        seen = []

        for segment in segment_collection:
            if segment in seen:
                logger.info(f"Found duplicate segment: {segment}")


def _flatten_news(lyric_segments: "Segments") -> "Segments":
    segments: Segments = []
    for segment in lyric_segments:
        if isinstance(segment, NewsMetaSegment):
            segments.extend(segment.news_segments)
        else:
            segments.append(segment)

    return segments


def _merge_noisy_segments(lyric_segments: "Segments", show_note_segments: "Segments") -> None:
    lyric_segment = _get_segment_of_type(NoisySegment, lyric_segments)
    show_note_segment = _get_segment_of_type(NoisySegment, show_note_segments)
    if lyric_segment and show_note_segment:
        lyric_segment.last_week_answer = show_note_segment.last_week_answer


def _merge_science_or_fiction_segments(lyric_segments: "Segments", show_note_segments: "Segments") -> None:
    lyric_segment = _get_segment_of_type(ScienceOrFictionSegment, lyric_segments)
    show_note_segment = _get_segment_of_type(ScienceOrFictionSegment, show_note_segments)
    if lyric_segment and show_note_segment:
        lyric_segment.items = show_note_segment.items


def _get_segment_of_type(segment_type: type[T], segments: "Segments") -> "T | None":
    for segment in segments:
        if isinstance(segment, segment_type):
            return segment

    return None
