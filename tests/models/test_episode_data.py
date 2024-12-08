from unittest.mock import MagicMock

from transcription_bot.models import episode_data
from transcription_bot.models.data_models import EpisodeImage
from transcription_bot.models.episode_segments import TranscribedSegments


def test_create_episode_metadata(podcast_rss_entry: episode_data.PodcastRssEntry, image: EpisodeImage):
    episode_data.EpisodeMetadata(podcast_rss_entry, "fake_lyrics", b"fake_show_notes", image)


def test_create_episode_data(
    episode_metadata: episode_data.EpisodeMetadata, segments: TranscribedSegments, transcript: MagicMock
):
    episode_data.EpisodeData(episode_metadata, segments, transcript)
