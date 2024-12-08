from transcription_bot.models.episode_data import EpisodeMetadata
from transcription_bot.models.episode_segments import (
    NewsMetaSegment,
    NoisySegment,
    RawSegments,
    ScienceOrFictionSegment,
)
from transcription_bot.parsers.lyrics import parse_lyrics
from transcription_bot.parsers.show_notes import parse_show_notes
from transcription_bot.parsers.summary_text import parse_summary_text
from transcription_bot.utils.global_logger import logger
from transcription_bot.utils.helpers import get_first_segment_of_type


def merge_segments(
    lyric_segments: RawSegments,
    show_note_segments: RawSegments,
    summary_text_segments: RawSegments,
) -> RawSegments:
    """Join segments from different collections and flag any potential issues.

    NOTE: This modifies the elements of the `lyric_segments` collection in place.
    """
    _find_duplicate_segments(lyric_segments, show_note_segments, summary_text_segments)

    segments = _flatten_news(lyric_segments)

    _merge_noisy_segments(segments, show_note_segments)
    _merge_science_or_fiction_segments(segments, show_note_segments)

    return segments


def extract_episode_segments_from_episode_metadata(episode_metadata: EpisodeMetadata) -> RawSegments:
    """Extracts segments from episode metadata.

    This function takes the episode metadata and parses the lyrics, show notes, and summary text
    into separate segments. It then merges the segments together to capture all the data.
    """
    lyric_segments = parse_lyrics(episode_metadata.lyrics)
    show_note_segments = parse_show_notes(episode_metadata.show_notes)
    summary_text_segments = parse_summary_text(episode_metadata.podcast.summary)

    return merge_segments(lyric_segments, show_note_segments, summary_text_segments)


def _find_duplicate_segments(*segment_collections: RawSegments) -> None:
    for segment_collection in segment_collections:
        seen = []

        for segment in segment_collection:
            if segment in seen:
                logger.error(f"Found duplicate segment: {segment}")


def _flatten_news(lyric_segments: RawSegments) -> RawSegments:
    segments = []
    for segment in lyric_segments:
        if isinstance(segment, NewsMetaSegment):
            segments.extend(segment.news_segments)
        else:
            segments.append(segment)

    return RawSegments(segments)


def _merge_noisy_segments(lyric_segments: RawSegments, show_note_segments: RawSegments) -> None:
    lyric_segment = get_first_segment_of_type(lyric_segments, NoisySegment)
    show_note_segment = get_first_segment_of_type(show_note_segments, NoisySegment)
    if lyric_segment and show_note_segment:
        lyric_segment.last_week_answer = show_note_segment.last_week_answer


def _merge_science_or_fiction_segments(lyric_segments: RawSegments, show_note_segments: RawSegments) -> None:
    lyric_segment = get_first_segment_of_type(lyric_segments, ScienceOrFictionSegment)
    show_note_segment = get_first_segment_of_type(show_note_segments, ScienceOrFictionSegment)
    if lyric_segment and show_note_segment:
        lyric_segment.raw_items = show_note_segment.raw_items
