"""Models which are composed of all other models and represent large chunks of data about a podcast episode."""

from pydantic.dataclasses import dataclass

from transcription_bot.models.data_models import EpisodeImage, PodcastRssEntry
from transcription_bot.models.episode_segments import TranscribedSegments
from transcription_bot.models.simple_models import DiarizedTranscript


@dataclass
class EpisodeRawData:
    """Raw data about a podcast episode.

    Attributes:
        podcast: Data from the rss feed.
        lyrics: The lyrics that were embedded in the MP3 file.
        show_notes: The show notes of the episode from the website.
        image: The image for the episode.
    """

    rss_entry: PodcastRssEntry
    lyrics: str
    show_notes: bytes
    image: EpisodeImage


@dataclass
class EpisodeData:
    """Full data about a podcast episode."""

    raw_data: EpisodeRawData
    segments: TranscribedSegments
    transcript: DiarizedTranscript
