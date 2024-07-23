from typing import TYPE_CHECKING

from sgu.episode_segments import IntroSegment, SegmentSource

if TYPE_CHECKING:
    from sgu.episode_segments import Segments
    from sgu.transcription import DiarizedTranscript


def add_transcript_to_segments(transcript: "DiarizedTranscript", episode_segments: "Segments") -> "Segments":
    """Add the transcript to the episode segments."""
    segments: Segments = [IntroSegment(source=SegmentSource.HARDCODED, start_time=0), *episode_segments]
    transcript = transcript.copy()

    # This defines the "leftmost" segment. The one waiting to have the endpoint set.
    last_episode_segment_with_start_time = segments[0]

    for segment in segments[1:]:
        segment.start_time = segment.get_start_time(transcript)

        if not segment.start_time:
            # If the segment does not have a start time, it's useless to us.
            continue

        # Fill in the transcript for the last segment
        transcript_segments_for_last_episode_segment = []

        while transcript and transcript[0]["end"] < segment.start_time:
            transcript_segments_for_last_episode_segment.append(transcript.pop(0))

        last_episode_segment_with_start_time.transcript = _join_speaker_segments_in_transcript(
            transcript_segments_for_last_episode_segment
        )

        last_episode_segment_with_start_time = segment

    last_episode_segment_with_start_time.transcript = _join_speaker_segments_in_transcript(transcript)

    return _sort_segments(segments)


def _sort_segments(segments: "Segments") -> "Segments":
    with_starts = []
    without_starts = []
    for segment in segments:
        if segment.start_time:
            with_starts.append(segment)
        else:
            without_starts.append(segment)

    return [*with_starts, *without_starts]


def _join_speaker_segments_in_transcript(transcript: "DiarizedTranscript") -> "DiarizedTranscript":
    current_speaker = None

    speaker_chunks = []
    for transcript_chunk in transcript:
        if transcript_chunk["speaker"] != current_speaker:
            speaker_chunks.append(transcript_chunk)
            current_speaker = transcript_chunk["speaker"]
        else:
            speaker_chunks[-1]["text"] += " " + transcript_chunk["text"]
            speaker_chunks[-1]["end"] = transcript_chunk["end"]

    for chunk in transcript:
        if "SPEAKER_" in chunk["speaker"]:
            name = "US#" + chunk["speaker"].split("_")[1]
            chunk["speaker"] = name
        else:
            chunk["speaker"] = chunk["speaker"][0]

    return speaker_chunks
