import itertools
from typing import TYPE_CHECKING

from sgu.episode_segments import IntroSegment
from sgu.global_logger import logger
from sgu.llm_interface import ask_llm_for_segment_start

if TYPE_CHECKING:
    from sgu.episode_segments import Segments
    from sgu.transcription import DiarizedTranscript


def add_transcript_to_segments(transcript: "DiarizedTranscript", episode_segments: "Segments") -> "Segments":
    """Add the transcript to the episode segments."""
    segments: Segments = [IntroSegment(start_time=0), *episode_segments]
    transcript = transcript.copy()

    last_start_time = 0

    for left_segment, right_segment in itertools.pairwise(segments):
        # The left segment should have a start time, if it doesn't,
        # we set it to the last start time we know of.

        if left_segment.start_time is None:
            left_segment.start_time = last_start_time

        right_segment.start_time = right_segment.get_start_time(transcript)

        if not right_segment.start_time:
            right_segment.start_time = ask_llm_for_segment_start(right_segment, transcript)

            if not right_segment.start_time:
                logger.info(f"No start time found for segment: {right_segment}")
                logger.warning(f"Segment will not get any transcript: {left_segment}")
                continue

        if right_segment.start_time:
            last_start_time = right_segment.start_time

        # Start times are done, now we fill in the transcript for the left segment.
        counter = 0
        while transcript and transcript[0]["end"] < right_segment.start_time:
            left_segment.transcript.append(transcript.pop(0))
            counter += 1

        logger.debug(f"Added {counter} transcript chunks to {left_segment.__class__.__name__}")

    # The last segment gets the rest of the transcript.
    segments[-1].transcript.extend(transcript)
    logger.debug(f"Added {len(transcript)} transcript chunks to {segments[-1].__class__.__name__}")

    for segment in segments:
        if not segment.transcript:
            logger.warning(f"Segment {segment} has no transcript")

    return segments
