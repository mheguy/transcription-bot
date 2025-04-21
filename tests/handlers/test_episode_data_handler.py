from unittest.mock import Mock, create_autospec

import pytest

from transcription_bot.handlers import episode_data_handler
from transcription_bot.models.data_models import EpisodeImage, PodcastRssEntry
from transcription_bot.models.episode_data import EpisodeRawData
from transcription_bot.models.episode_segments.simple_segments import (
    ForgottenSuperheroesOfScienceSegment,
    IntroSegment,
    OutroSegment,
    QuickieSegment,
)
from transcription_bot.models.episode_segments.type_hints import RawSegments
from transcription_bot.models.simple_models import DiarizedTranscript

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


@pytest.fixture(name="diarized_transcript")
def mock_diarized_transcript() -> DiarizedTranscript:
    return [
        {"speaker": "Host", "text": HOST_LINE_1, "start": HOST_LINE_1_START_TIME, "end": GUEST_LINE_1_START_TIME},
        {"speaker": "Guest", "text": GUEST_LINE_1, "start": GUEST_LINE_1_START_TIME, "end": HOST_LINE_2_START_TIME},
        {"speaker": "Host", "text": HOST_LINE_2, "start": HOST_LINE_2_START_TIME, "end": GUEST_LINE_2_START_TIME},
        {"speaker": "Guest", "text": GUEST_LINE_2, "start": GUEST_LINE_2_START_TIME, "end": HOST_LINE_3_START_TIME},
        {"speaker": "Host", "text": HOST_LINE_3, "start": HOST_LINE_3_START_TIME, "end": TRANSCRIPTION_END_TIME},
    ]


@pytest.fixture(name="episode_image")
def mock_episode_image() -> EpisodeImage:
    return EpisodeImage("fake_url", "fake_name")


@pytest.fixture(name="episode_raw_data")
def mock_episode_raw_data(podcast_rss_entry: PodcastRssEntry) -> EpisodeRawData:
    return EpisodeRawData(
        rss_entry=podcast_rss_entry,
        lyrics="Test lyrics",
        show_notes=b"""
        <main class="podcast-main">
            <h3>Science News</h3>
            <div>First news item</div>
            <h3>Interview</h3>
            <div>Interview with a scientist</div>
        </main>
        """,
        image=EpisodeImage("fake_url", "fake_name"),
    )


def test_get_transcript_between_times_with_slice_of_transcript(diarized_transcript: DiarizedTranscript):
    # Act
    result = episode_data_handler.get_transcript_between_times(
        diarized_transcript, GUEST_LINE_1_START_TIME, GUEST_LINE_2_START_TIME
    )

    # Assert
    assert len(result) == 2
    assert result[0]["text"] == GUEST_LINE_1
    assert result[1]["text"] == HOST_LINE_2


def test_get_transcript_between_times_with_no_transcript_in_range(diarized_transcript: DiarizedTranscript):
    # Act
    result = episode_data_handler.get_transcript_between_times(
        diarized_transcript, TRANSCRIPTION_END_TIME + 5, TRANSCRIPTION_END_TIME + 10
    )

    # Assert
    assert len(result) == 0


def test_get_transcript_between_times_from_start(diarized_transcript: DiarizedTranscript):
    # Act
    result = episode_data_handler.get_transcript_between_times(
        diarized_transcript, HOST_LINE_1_START_TIME, HOST_LINE_2_START_TIME
    )

    # Assert
    assert len(result) == 2
    assert result[0]["text"] == HOST_LINE_1


def test_get_partial_transcript_for_start_time_with_skip(diarized_transcript: DiarizedTranscript):
    # Act
    result = episode_data_handler.get_partial_transcript_for_start_time(
        diarized_transcript, 1, GUEST_LINE_1_START_TIME, HOST_LINE_3_START_TIME
    )

    # Assert
    assert len(result) == 2  # Expecting 2 chunks between 5.0 and 20.0, skipping 1
    assert result[0]["text"] == HOST_LINE_2


def test_get_partial_transcript_for_start_time_with_no_skip(diarized_transcript: DiarizedTranscript):
    # Act
    result = episode_data_handler.get_partial_transcript_for_start_time(
        diarized_transcript, 0, HOST_LINE_1_START_TIME, HOST_LINE_2_START_TIME
    )

    # Assert
    assert len(result) == 2
    assert result[0]["text"] == HOST_LINE_1


def test_add_transcript_to_segments(
    episode_raw_data: Mock, diarized_transcript: DiarizedTranscript, monkeypatch: pytest.MonkeyPatch
):
    # Arrange
    mock_llm = create_autospec(episode_data_handler.get_segment_start_from_llm)
    monkeypatch.setattr(episode_data_handler, "get_segment_start_from_llm", mock_llm)
    # Configure mock to return a fixed timestamp
    mock_llm.return_value = HOST_LINE_2_START_TIME

    # Create some test segments
    segments = RawSegments(
        [
            QuickieSegment(
                title="Test News",
                subject="Science",
                url="http://example.com",
            ),
            ForgottenSuperheroesOfScienceSegment(),
        ]
    )

    # Add transcript to segments
    # Act
    result = episode_data_handler.add_transcript_to_segments(episode_raw_data, diarized_transcript, segments)

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
    assert result[-1].end_time == diarized_transcript[-1]["end"]

    # Calls for: Quickie, Forgotten, and Outro
    assert mock_llm.call_count == 3
