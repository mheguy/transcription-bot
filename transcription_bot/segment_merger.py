from transcription_bot.episode_segments import (
    NewsMetaSegment,
    NoisySegment,
    ScienceOrFictionSegment,
    Segments,
    get_first_segment_of_type,
)
from transcription_bot.global_logger import logger


def merge_segments(
    lyric_segments: Segments,
    show_note_segments: Segments,
    summary_text_segments: Segments,
) -> Segments:
    """Join segments from different collections and flag any potential issues.

    NOTE: This modifies the elements of the `lyric_segments` collection in place.
    """
    _find_duplicate_segments(lyric_segments, show_note_segments, summary_text_segments)

    segments = _flatten_news(lyric_segments)

    _merge_noisy_segments(segments, show_note_segments)
    _merge_science_or_fiction_segments(segments, show_note_segments)

    return segments


def _find_duplicate_segments(*segment_collections: Segments) -> None:
    for segment_collection in segment_collections:
        seen = []

        for segment in segment_collection:
            if segment in seen:
                logger.error(f"Found duplicate segment: {segment}")


def _flatten_news(lyric_segments: Segments) -> Segments:
    segments: Segments = []
    for segment in lyric_segments:
        if isinstance(segment, NewsMetaSegment):
            segments.extend(segment.news_segments)
        else:
            segments.append(segment)

    return segments


def _merge_noisy_segments(lyric_segments: Segments, show_note_segments: Segments) -> None:
    lyric_segment = get_first_segment_of_type(lyric_segments, NoisySegment)
    show_note_segment = get_first_segment_of_type(show_note_segments, NoisySegment)
    if lyric_segment and show_note_segment:
        lyric_segment.last_week_answer = show_note_segment.last_week_answer


def _merge_science_or_fiction_segments(lyric_segments: Segments, show_note_segments: Segments) -> None:
    lyric_segment = get_first_segment_of_type(lyric_segments, ScienceOrFictionSegment)
    show_note_segment = get_first_segment_of_type(show_note_segments, ScienceOrFictionSegment)
    if lyric_segment and show_note_segment:
        lyric_segment.raw_items = show_note_segment.raw_items
