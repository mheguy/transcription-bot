from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from transcription_bot import caching
from transcription_bot.episode_segments import BaseSegment
from transcription_bot.parsers.rss_feed import PodcastEpisode
from transcription_bot.transcription._diarized_transcript import DiarizedTranscript

# Test constants
TEST_EPISODE_NUMBER = "123"
TEST_URL = "https://example.com"
TEST_DATA_KEY = "data"
TEST_DATA_VALUE = "test"
TEST_LLM_RESULT = 42.0


@pytest.fixture()
def mock_podcast_episode():
    episode = MagicMock(spec=PodcastEpisode)
    episode.episode_number = TEST_EPISODE_NUMBER
    return episode


@pytest.fixture()
def mock_segment():
    return MagicMock(spec=BaseSegment)


@pytest.fixture()
def mock_transcript():
    transcript = MagicMock(spec=DiarizedTranscript)
    transcript.__getitem__.return_value = {"start": 10.0}
    return transcript


def test_cache_for_episode(tmp_path: Path, mock_podcast_episode: MagicMock):
    # Arrange
    test_func_mock = MagicMock(return_value={TEST_DATA_KEY: TEST_DATA_VALUE})

    with patch("transcription_bot.caching._CACHE_FOLDER", tmp_path):

        @caching.cache_for_episode
        def test_func(_episode: PodcastEpisode) -> dict[str, str]:  # noqa: PT019
            return test_func_mock(_episode)

        # Act
        # First call - should execute function and cache
        result1 = test_func(mock_podcast_episode)
        # Second call - should use cache
        result2 = test_func(mock_podcast_episode)

        # Assert
        assert result1 == {TEST_DATA_KEY: TEST_DATA_VALUE}
        assert result1 == result2
        # Verify the underlying function was only called once
        test_func_mock.assert_called_once_with(mock_podcast_episode)


def test_cache_url_title(tmp_path: Path):
    # Arrange
    get_title_mock = MagicMock(side_effect=lambda url: f"Title for {url}")

    with patch("transcription_bot.caching._CACHE_FOLDER", tmp_path):

        @caching.cache_url_title
        def get_title(url: str) -> str:
            return get_title_mock(url)

        # Act
        # First call - should execute function and cache
        result1 = get_title(TEST_URL)
        # Second call - should use cache
        result2 = get_title(TEST_URL)

        # Assert
        assert result1 == f"Title for {TEST_URL}"
        assert result2 == result1
        # Verify the underlying function was only called once
        get_title_mock.assert_called_once_with(TEST_URL)


def test_cache_llm(
    tmp_path: Path, mock_podcast_episode: MagicMock, mock_segment: MagicMock, mock_transcript: MagicMock
):
    # Arrange
    llm_mock = MagicMock(return_value=TEST_LLM_RESULT)

    with patch("transcription_bot.caching._CACHE_FOLDER", tmp_path):

        @caching.cache_llm
        def test_llm(_episode: PodcastEpisode, _segment: BaseSegment, _transcript: DiarizedTranscript) -> float:  # noqa: PT019
            return llm_mock(_episode, _segment, _transcript)

        # Act
        # First call - should execute function and cache
        result1 = test_llm(mock_podcast_episode, mock_segment, mock_transcript)
        # Second call - should use cache
        result2 = test_llm(mock_podcast_episode, mock_segment, mock_transcript)

        # Assert
        assert result1 == TEST_LLM_RESULT
        assert result2 == result1
        # Verify the underlying function was only called once
        llm_mock.assert_called_once_with(mock_podcast_episode, mock_segment, mock_transcript)


def test_cache_for_episode_different_episodes(tmp_path: Path):
    # Arrange
    test_func_mock = MagicMock(side_effect=lambda ep: {TEST_DATA_KEY: f"{TEST_DATA_VALUE}_{ep.episode_number}"})

    with patch("transcription_bot.caching._CACHE_FOLDER", tmp_path):

        @caching.cache_for_episode
        def test_func(episode: PodcastEpisode) -> dict[str, str]:
            return test_func_mock(episode)

        episode1 = MagicMock(spec=PodcastEpisode)
        episode1.episode_number = "1"
        episode2 = MagicMock(spec=PodcastEpisode)
        episode2.episode_number = "2"

        # Act
        result1 = test_func(episode1)
        result2 = test_func(episode2)

        # Assert
        assert result1 != result2
        assert result1[TEST_DATA_KEY] == f"{TEST_DATA_VALUE}_1"
        assert result2[TEST_DATA_KEY] == f"{TEST_DATA_VALUE}_2"
        # Verify each episode called the function once
        assert test_func_mock.call_count == 2
        test_func_mock.assert_any_call(episode1)
        test_func_mock.assert_any_call(episode2)
