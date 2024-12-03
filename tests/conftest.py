from unittest.mock import MagicMock

import pytest

from tests.test_caching import TEST_EPISODE_NUMBER
from transcription_bot.config import CONFIG_FILE, config
from transcription_bot.data_models import DiarizedTranscript, PodcastRssEntry
from transcription_bot.episode_segments import BaseSegment


@pytest.fixture(autouse=True, scope="session")
def clean_config() -> None:
    """Disable caching and remove all environment variables for tests (to prevent external calls)."""
    config.validators.clear()
    config.load_file(CONFIG_FILE)


@pytest.fixture()
def enable_local_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """Enable caching for tests."""
    monkeypatch.setattr(config, "local_mode", True)


@pytest.fixture(name="podcast_episode")
def mock_podcast_episode() -> MagicMock:
    episode = MagicMock(spec=PodcastRssEntry)
    episode.episode_number = TEST_EPISODE_NUMBER
    return episode


@pytest.fixture(name="segment")
def mock_segment() -> MagicMock:
    return MagicMock(spec=BaseSegment)


@pytest.fixture(name="transcript")
def mock_transcript() -> MagicMock:
    transcript = MagicMock(spec=DiarizedTranscript)
    transcript.__getitem__.return_value = {"start": 10.0}
    return transcript
