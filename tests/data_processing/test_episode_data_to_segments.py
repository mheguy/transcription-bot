from datetime import date
from unittest.mock import Mock, patch

import pytest

from transcription_bot.data_processing import episode_data_to_segments
from transcription_bot.models.data_models import DiarizedTranscript, EpisodeMetadata, PodcastRssEntry
from transcription_bot.models.episode_segments import (
    ForgottenSuperheroesOfScienceSegment,
    IntroSegment,
    OutroSegment,
    QuickieSegment,
    Segments,
)

HOST_LINE_1 = "Welcome to the show"
HOST_LINE_1_START_TIME = 0.0
GUEST_LINE_1 = "Thanks for having me"
GUEST_LINE_1_START_TIME = 5.0
HOST_LINE_2 = "Let's talk about news"
HOST_LINE_2_START_TIME = 10.0
GUEST_LINE_2 = "Here's the first story"
GUEST_LINE_2_START_TIME = 15.0
HOST_LINE_3 = "That's all for today"
HOST_LINE_3_START_TIME = 20.0
TRANSCRIPTION_END_TIME = 25.0


@pytest.fixture()
def sample_diarized_transcript() -> DiarizedTranscript:
    return [
        {"speaker": "Host", "text": HOST_LINE_1, "start": HOST_LINE_1_START_TIME, "end": GUEST_LINE_1_START_TIME},
        {"speaker": "Guest", "text": GUEST_LINE_1, "start": GUEST_LINE_1_START_TIME, "end": HOST_LINE_2_START_TIME},
        {"speaker": "Host", "text": HOST_LINE_2, "start": HOST_LINE_2_START_TIME, "end": GUEST_LINE_2_START_TIME},
        {"speaker": "Guest", "text": GUEST_LINE_2, "start": GUEST_LINE_2_START_TIME, "end": HOST_LINE_3_START_TIME},
        {"speaker": "Host", "text": HOST_LINE_3, "start": HOST_LINE_3_START_TIME, "end": TRANSCRIPTION_END_TIME},
    ]


@pytest.fixture()
def sample_podcast_episode() -> PodcastRssEntry:
    return PodcastRssEntry(
        episode_number=123,
        official_title="Test Episode",
        summary="This is a test episode summary",
        download_url="http://example.com/download",
        episode_url="http://example.com/episode",
        date=date(2000, 1, 1),
    )


@pytest.fixture()
def sample_episode_metadata(sample_podcast_episode: PodcastRssEntry) -> EpisodeMetadata:
    return EpisodeMetadata(
        podcast=sample_podcast_episode,
        lyrics="Test lyrics",
        show_notes=b"""
        <main class="podcast-main">
            <h3>Science News</h3>
            <div>First news item</div>
            <h3>Interview</h3>
            <div>Interview with a scientist</div>
        </main>
        """,
    )


def test_get_transcript_between_times_with_slice_of_transcript(sample_diarized_transcript: DiarizedTranscript):
    # Act
    result = episode_data_to_segments.get_transcript_between_times(
        sample_diarized_transcript, GUEST_LINE_1_START_TIME, GUEST_LINE_2_START_TIME
    )

    # Assert
    assert len(result) == 2
    assert result[0]["text"] == GUEST_LINE_1
    assert result[1]["text"] == HOST_LINE_2


def test_get_transcript_between_times_with_no_transcript_in_range(sample_diarized_transcript: DiarizedTranscript):
    # Act
    result = episode_data_to_segments.get_transcript_between_times(
        sample_diarized_transcript, TRANSCRIPTION_END_TIME + 5, TRANSCRIPTION_END_TIME + 10
    )

    # Assert
    assert len(result) == 0


def test_get_transcript_between_times_from_start(sample_diarized_transcript: DiarizedTranscript):
    # Act
    result = episode_data_to_segments.get_transcript_between_times(
        sample_diarized_transcript, HOST_LINE_1_START_TIME, HOST_LINE_2_START_TIME
    )

    # Assert
    assert len(result) == 2
    assert result[0]["text"] == HOST_LINE_1


def test_get_partial_transcript_for_start_time_with_skip(sample_diarized_transcript: DiarizedTranscript):
    # Act
    result = episode_data_to_segments.get_partial_transcript_for_start_time(
        sample_diarized_transcript, 1, GUEST_LINE_1_START_TIME, HOST_LINE_3_START_TIME
    )

    # Assert
    assert len(result) == 2  # Expecting 2 chunks between 5.0 and 20.0, skipping 1
    assert result[0]["text"] == HOST_LINE_2


def test_get_partial_transcript_for_start_time_with_no_skip(sample_diarized_transcript: DiarizedTranscript):
    # Act
    result = episode_data_to_segments.get_partial_transcript_for_start_time(
        sample_diarized_transcript, 0, HOST_LINE_1_START_TIME, HOST_LINE_2_START_TIME
    )

    # Assert
    assert len(result) == 2
    assert result[0]["text"] == HOST_LINE_1


@patch("transcription_bot.data_processing.episode_data_to_segments.ask_llm_for_segment_start")
def test_add_transcript_to_segments(
    mock_llm: Mock, sample_podcast_episode: PodcastRssEntry, sample_diarized_transcript: DiarizedTranscript
):
    # Arrange
    # Configure mock to return a fixed timestamp
    mock_llm.return_value = HOST_LINE_2_START_TIME

    # Create some test segments
    segments: Segments = [
        QuickieSegment(
            title="Test News",
            subject="Science",
            url="http://example.com",
        ),
        ForgottenSuperheroesOfScienceSegment(),
    ]

    # Add transcript to segments
    # Act
    result = episode_data_to_segments.add_transcript_to_segments(
        sample_podcast_episode, sample_diarized_transcript, segments
    )

    # Verify segments have correct transcripts
    # Assert
    assert len(result) == 4
    assert isinstance(result[0], IntroSegment)
    assert isinstance(result[1], QuickieSegment)
    assert isinstance(result[2], ForgottenSuperheroesOfScienceSegment)
    assert isinstance(result[3], OutroSegment)

    # Verify transcript content and timing
    assert len(result[0].transcript) > 0
    assert result[0].transcript[0]["text"] == HOST_LINE_1
    assert result[0].end_time == HOST_LINE_2_START_TIME  # Should match mock LLM response
    assert result[-1].end_time == sample_diarized_transcript[-1]["end"]

    # Calls for: Quickie, Forgotten, and Outro
    assert mock_llm.call_count == 3
