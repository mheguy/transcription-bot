"""Models which are composed of all other models and represent large chunks of data about a podcast episode."""

from pydantic.dataclasses import dataclass

from transcription_bot.models.data_models import EpisodeImage, PodcastRssEntry
from transcription_bot.models.episode_segments import TranscribedSegments
from transcription_bot.models.simple_models import DiarizedTranscript


@dataclass
class EpisodeMetadata:
    """Metadata about a podcast episode.

    Attributes:
        podcast: Data from the rss feed
        lyrics: The lyrics that were embedded in the MP3 file.
        show_notes: The show notes of the episode from the website.
    """

    podcast: PodcastRssEntry
    lyrics: str
    show_notes: bytes
    image: EpisodeImage


@dataclass
class EpisodeData:
    """Full data about a podcast episode.

    Attributes:
        metadata: The metadata for an episode
        segments: The segments of the episode
    """

    metadata: EpisodeMetadata
    segments: TranscribedSegments
    transcript: DiarizedTranscript
