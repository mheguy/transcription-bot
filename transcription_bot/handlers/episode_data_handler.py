import itertools

from loguru import logger
from openai.types.chat.chat_completion_content_part_param import ChatCompletionContentPartParam

from transcription_bot.interfaces.llm_interface import get_segment_start_from_llm, get_sof_metadata_from_llm
from transcription_bot.models.data_models import PodcastRssEntry
from transcription_bot.models.episode_data import EpisodeData, EpisodeRawData
from transcription_bot.models.episode_segments import (
    IntroSegment,
    OutroSegment,
    RawSegments,
    ScienceOrFictionLlmData,
    ScienceOrFictionSegment,
    TranscribedSegments,
)
from transcription_bot.models.simple_models import DiarizedTranscript

_THIRTY_MINUTES = 30 * 60


def create_episode_data(
    episode_raw_data: EpisodeRawData,
    transcript: DiarizedTranscript,
    episode_segments: RawSegments,
) -> EpisodeData:
    """Create the episode data object."""
    transcribed_segments = add_transcript_to_segments(episode_raw_data, transcript, episode_segments)

    enhance_transcribed_segments(episode_raw_data, transcribed_segments)

    return EpisodeData(episode_raw_data, transcribed_segments, transcript)


def add_transcript_to_segments(
    episode_raw_data: EpisodeRawData, transcript: DiarizedTranscript, episode_segments: RawSegments
) -> TranscribedSegments:
    """Add the transcript to the episode segments."""
    partial_transcript: DiarizedTranscript = []
    segments = TranscribedSegments([IntroSegment(start_time=0), *episode_segments, OutroSegment()])

    segments[-1].end_time = transcript[-1]["end"]

    last_start_time = 0

    for left_segment, right_segment in itertools.pairwise(segments):
        # The left segment should have a start time, if it doesn't,
        # we set it to the last start time we know of.
        if not left_segment.start_time:
            left_segment.start_time = last_start_time

        partial_transcript = get_partial_transcript_for_start_time(
            transcript,
            2,
            left_segment.start_time,
            left_segment.start_time + _THIRTY_MINUTES,
        )

        right_segment.start_time = right_segment.get_start_time(partial_transcript)

        if not right_segment.start_time:
            right_segment.start_time = get_segment_start_from_llm(
                episode_raw_data.rss_entry.episode_number, right_segment, partial_transcript
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
            transcript,
            segment.start_time if segment.start_time else 0,
            segment.end_time,
        )
        if not segment.transcript:
            logger.error(f"Segment {segment} has no transcript")
        else:
            logger.debug(
                f"Segment {segment.__class__.__name__}: {len(segment.transcript)} transcript chunks, {segment.duration:.1f} minutes"
            )

    return segments


def get_transcript_between_times(transcript: DiarizedTranscript, start: float, end: float) -> DiarizedTranscript:
    """Get the transcript between two times."""
    return [c for c in transcript if start <= c["start"] < end]


def get_partial_transcript_for_start_time(
    transcript: DiarizedTranscript, transcript_chunks_to_skip: int, start: float, end: float
) -> DiarizedTranscript:
    """Get the transcript between two times, skipping the first n chunks."""
    return get_transcript_between_times(transcript, start, end)[transcript_chunks_to_skip:]


def enhance_transcribed_segments(episode_raw_data: EpisodeRawData, segments: TranscribedSegments) -> None:
    """Enhance segments with metadata that an LLM can infer."""
    if sof_segment := next((seg for seg in segments if isinstance(seg, ScienceOrFictionSegment)), None):
        sof_segment.metadata = get_sof_segment_metadata(episode_raw_data.rss_entry, sof_segment)


def get_sof_segment_metadata(rss_entry: PodcastRssEntry, segment: ScienceOrFictionSegment) -> ScienceOrFictionLlmData:
    """Get the metadata for a Science or Fiction segment."""
    transcript: list[ChatCompletionContentPartParam] = []
    for segment_chunk in segment.transcript:
        text = f"({segment_chunk['start']:0.2f}-{segment_chunk['end']:0.2f}) [{segment_chunk['speaker']}] {segment_chunk['text']}"
        transcript.append({"type": "text", "text": text})

    return get_sof_metadata_from_llm(rss_entry, transcript)
