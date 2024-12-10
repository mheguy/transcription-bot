from datetime import date
from unittest.mock import MagicMock

import pytest

from transcription_bot.models.data_models import EpisodeImage, PodcastRssEntry
from transcription_bot.models.episode_data import EpisodeRawData
from transcription_bot.models.episode_segments import BaseSegment, TranscribedSegments
from transcription_bot.models.simple_models import DiarizedTranscript
from transcription_bot.utils.config import CONFIG_FILE, config


@pytest.fixture(autouse=True, scope="session")
def clean_config() -> None:
    """Disable caching and remove all environment variables for tests (to prevent external calls)."""
    config.validators.clear()
    config.load_file(CONFIG_FILE)


@pytest.fixture()
def enable_local_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """Enable caching for tests."""
    monkeypatch.setattr(config, "local_mode", True)


# region Mocked models
@pytest.fixture(name="episode_raw_data")
def mock_episode_raw_data(podcast_rss_entry: PodcastRssEntry, image: EpisodeImage) -> EpisodeRawData:
    return EpisodeRawData(podcast_rss_entry, "fake_lyrics", b"fake_show_notes", image)


@pytest.fixture(name="image")
def mock_image() -> EpisodeImage:
    return EpisodeImage("fake_url", "fake_name")


@pytest.fixture(name="podcast_rss_entry")
def mock_podcast_rss_entry() -> PodcastRssEntry:
    return PodcastRssEntry(
        episode_number=0,
        official_title="fake_official_title",
        summary="fake_summary",
        raw_download_url="fake_raw_download_url",
        episode_url="fake_episode_url",
        date=date(2000, 1, 1),
    )


@pytest.fixture(name="segment")
def mock_segment() -> MagicMock:
    return MagicMock(spec=BaseSegment)


@pytest.fixture(name="segments")
def mock_segments(segment: MagicMock) -> TranscribedSegments:
    return TranscribedSegments([segment])


@pytest.fixture(name="transcript")
def mock_transcript() -> MagicMock:
    transcript = MagicMock(spec=DiarizedTranscript)
    transcript.__getitem__.return_value = {"start": 10.0}
    return transcript


# endregion
