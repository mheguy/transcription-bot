from pathlib import Path
from unittest.mock import MagicMock, patch

from transcription_bot.models.data_models import PodcastRssEntry
from transcription_bot.utils import caching

# Test constants
TEST_URL = "https://example.com"
TEST_DATA_KEY = "data"
TEST_DATA_VALUE = "test"
TEST_LLM_RESULT = 42.0


def test_cache_for_episode(tmp_path: Path, podcast_rss_entry: PodcastRssEntry):
    # Arrange
    test_func_mock = MagicMock(return_value={TEST_DATA_KEY: TEST_DATA_VALUE})

    with patch("transcription_bot.utils.caching._CACHE_FOLDER", tmp_path):

        @caching.cache_for_episode
        def test_func(_episode: PodcastRssEntry) -> dict[str, str]:  # noqa: PT019
            return test_func_mock(_episode)

        # Act
        # First call - should execute function and cache
        result1 = test_func(podcast_rss_entry)
        # Second call - should use cache
        result2 = test_func(podcast_rss_entry)

        # Assert
        assert result1 == {TEST_DATA_KEY: TEST_DATA_VALUE}
        assert result1 == result2
        # Verify the underlying function was only called once
        test_func_mock.assert_called_once_with(podcast_rss_entry)


def test_cache_url_title(tmp_path: Path):
    # Arrange
    get_title_mock = MagicMock(side_effect=lambda url: f"Title for {url}")

    with patch("transcription_bot.utils.caching._CACHE_FOLDER", tmp_path):

        @caching.cache_for_str_arg
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


def test_cache_for_episode_different_episodes(tmp_path: Path):
    # Arrange
    test_func_mock = MagicMock(side_effect=lambda ep: {TEST_DATA_KEY: f"{TEST_DATA_VALUE}_{ep.episode_number}"})

    with patch("transcription_bot.utils.caching._CACHE_FOLDER", tmp_path):

        @caching.cache_for_episode
        def test_func(episode: PodcastRssEntry) -> dict[str, str]:
            return test_func_mock(episode)

        episode1 = MagicMock(spec=PodcastRssEntry)
        episode1.episode_number = "1"
        episode2 = MagicMock(spec=PodcastRssEntry)
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


def test_cache_for_episode_predicate_true(tmp_path: Path, podcast_rss_entry: PodcastRssEntry) -> None:
    test_func_mock = MagicMock(return_value={TEST_DATA_KEY: TEST_DATA_VALUE})

    with patch("transcription_bot.utils.caching._CACHE_FOLDER", tmp_path):

        @caching.cache_for_episode(should_cache=lambda _: True)
        def test_func(episode: PodcastRssEntry) -> dict[str, str]:
            return test_func_mock(episode)

        result1 = test_func(podcast_rss_entry)
        result2 = test_func(podcast_rss_entry)

        assert result1 == {TEST_DATA_KEY: TEST_DATA_VALUE}
        assert result2 == result1
        # Since predicate is True, function should be called only once
        test_func_mock.assert_called_once_with(podcast_rss_entry)


def test_cache_for_episode_predicate_false(tmp_path: Path, podcast_rss_entry: PodcastRssEntry) -> None:
    test_func_mock = MagicMock(return_value={TEST_DATA_KEY: TEST_DATA_VALUE})

    with patch("transcription_bot.utils.caching._CACHE_FOLDER", tmp_path):

        @caching.cache_for_episode(should_cache=lambda _: False)
        def test_func(episode: PodcastRssEntry) -> dict[str, str]:
            return test_func_mock(episode)

        result1 = test_func(podcast_rss_entry)
        result2 = test_func(podcast_rss_entry)

        assert result1 == {TEST_DATA_KEY: TEST_DATA_VALUE}
        assert result2 == result1
        # Since predicate is False, function should be called each time
        assert test_func_mock.call_count == 2
