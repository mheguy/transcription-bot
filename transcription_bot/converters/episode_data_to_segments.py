import itertools

from transcription_bot.data_models import DiarizedTranscript, EpisodeData, PodcastRssEntry
from transcription_bot.episode_segments import IntroSegment, OutroSegment, Segments
from transcription_bot.global_logger import logger
from transcription_bot.llm_interface import ask_llm_for_segment_start
from transcription_bot.parsers.lyrics import parse_lyrics
from transcription_bot.parsers.show_notes import parse_show_notes
from transcription_bot.parsers.summary_text import parse_summary_text
from transcription_bot.segment_merger import merge_segments

_THIRTY_MINUTES = 30 * 60


def add_transcript_to_segments(
    podcast_episode: PodcastRssEntry,
    raw_transcript: DiarizedTranscript,
    episode_segments: Segments,
) -> Segments:
    """Add the transcript to the episode segments."""
    partial_transcript: DiarizedTranscript = []
    segments: Segments = [IntroSegment(start_time=0), *episode_segments, OutroSegment()]

    segments[-1].end_time = raw_transcript[-1]["end"]

    last_start_time = 0

    for left_segment, right_segment in itertools.pairwise(segments):
        # The left segment should have a start time, if it doesn't,
        # we set it to the last start time we know of.
        if not left_segment.start_time:
            left_segment.start_time = last_start_time

        partial_transcript = get_partial_transcript_for_start_time(
            raw_transcript,
            2,
            left_segment.start_time,
            left_segment.start_time + _THIRTY_MINUTES,
        )

        right_segment.start_time = right_segment.get_start_time(partial_transcript)

        if not right_segment.start_time:
            right_segment.start_time = ask_llm_for_segment_start(
                podcast_episode.episode_number, right_segment, partial_transcript
            )

            if not right_segment.start_time:
                logger.info(f"No start time found for segment: {right_segment}")
                logger.warning(f"Segment will not get any transcript: {left_segment}")
                continue

        if right_segment.start_time:
            last_start_time = right_segment.start_time

        left_segment.end_time = right_segment.start_time

    for segment in segments:
        segment.transcript = get_transcript_between_times(
            raw_transcript,
            segment.start_time if segment.start_time else 0,
            segment.end_time,
        )
        if not segment.transcript:
            logger.warning(f"Segment {segment} has no transcript")
        else:
            logger.debug(
                f"Segment {segment.__class__.__name__}: {len(segment.transcript)} transcript chunks, {segment.duration:1f} minutes"
            )

    return segments


def convert_episode_data_to_episode_segments(episode_data: EpisodeData) -> Segments:
    """Converts episode data into segments.

    This function takes the episode data and parses the lyrics, show notes, and summary text
    into separate segments. It then joins the segments together.

    Args:
        episode_data (EpisodeData): The episode data.

    Returns:
        Segments: The joined segments.
    """
    lyric_segments = parse_lyrics(episode_data.lyrics)
    show_note_segments = parse_show_notes(episode_data.show_notes)
    summary_text_segments = parse_summary_text(episode_data.podcast.summary)

    return merge_segments(lyric_segments, show_note_segments, summary_text_segments)


def get_transcript_between_times(transcript: DiarizedTranscript, start: float, end: float) -> DiarizedTranscript:
    """Get the transcript between two times."""
    return [c for c in transcript if start <= c["start"] < end]


def get_partial_transcript_for_start_time(
    transcript: DiarizedTranscript, transcript_chunks_to_skip: int, start: float, end: float
) -> DiarizedTranscript:
    """Get the transcript between two times, skipping the first n chunks."""
    return get_transcript_between_times(transcript, start, end)[transcript_chunks_to_skip:]
