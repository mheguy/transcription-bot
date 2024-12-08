from datetime import date

from transcription_bot.models import data_models
from transcription_bot.models.simple_models import EpisodeStatus


def test_create_sgu_list_entry():
    # Act
    data_models.SguListEntry("fake_episode", "fake-date", EpisodeStatus.UNKNOWN)


def test_create_episode_image():
    data_models.EpisodeImage("fake_url", "fake_name", "fake_caption")


def test_create_podcast_rss_entry():
    data_models.PodcastRssEntry(
        0, "fake_title", "fake_summary", "fake_download_url", "fake_episode_url", date(2000, 1, 1)
    )
