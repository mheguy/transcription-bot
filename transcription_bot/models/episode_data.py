from pydantic.dataclasses import dataclass

from transcription_bot.models.data_models import DiarizedTranscript, EpisodeImage, PodcastRssEntry
from transcription_bot.models.episode_segments import TranscribedSegments


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
