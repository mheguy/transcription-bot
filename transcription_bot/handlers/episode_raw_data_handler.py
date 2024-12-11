from io import BytesIO

from loguru import logger
from mutagen.id3 import ID3
from mutagen.id3._frames import TXXX, USLT
from requests import Session

from transcription_bot.interfaces.wiki import find_image_upload, upload_image_to_wiki
from transcription_bot.models.data_models import EpisodeImage, PodcastRssEntry
from transcription_bot.models.episode_data import EpisodeRawData
from transcription_bot.parsers.show_notes import get_episode_image_url
from transcription_bot.utils.caching import cache_for_episode
from transcription_bot.utils.exceptions import NoLyricsTagError
from transcription_bot.utils.helpers import download_file


def gather_raw_data(rss_entry: PodcastRssEntry, client: Session) -> EpisodeRawData:
    """Gather raw data for a podcast episode."""
    logger.info("Getting show data...")
    mp3 = get_audio_file(rss_entry, client)

    lyrics = get_lyrics_from_mp3(rss_entry, mp3)
    show_notes = get_show_notes(rss_entry, client)

    image = get_image_data(rss_entry, show_notes, client)

    return EpisodeRawData(rss_entry, lyrics, show_notes, image)


def get_lyrics_from_mp3(_rss_entry: PodcastRssEntry, raw_bytes: bytes) -> str:
    """Get the lyrics from an MP3 file."""
    audio = ID3(BytesIO(raw_bytes))

    frame: TXXX | USLT
    if (tag := audio.getall("TXXX:lyrics-eng")) or (tag := audio.getall("USLT::eng")):
        frame = tag[0]
    else:
        raise NoLyricsTagError("Could not find lyrics tag")

    result: str | list[str] | None = getattr(frame, "text", None)

    if result is None:
        raise ValueError("Could not find lyrics in tag")

    if isinstance(result, str):
        return result

    if len(result) > 1:
        raise ValueError("Multiple lyrics found in tag")

    return result[0]


@cache_for_episode
def get_audio_file(rss_entry: PodcastRssEntry, client: Session) -> bytes:
    """Retrieve the audio file for a podcast episode."""
    logger.info("Downloading episode mp3...")
    return download_file(rss_entry.download_url, client)


@cache_for_episode
def get_show_notes(rss_entry: PodcastRssEntry, client: Session) -> bytes:
    """Get the show notes from the website."""
    logger.info("Downloading show notes...")
    resp = client.get(rss_entry.episode_url)

    return resp.content


@cache_for_episode
def get_image_data(rss_entry: PodcastRssEntry, show_notes: bytes, client: Session) -> EpisodeImage:
    """Get the image data from the show notes."""
    logger.debug("Getting image data...")
    url = get_episode_image_url(show_notes)
    episode_number = rss_entry.episode_number

    episode_icon_name = find_image_upload(client, str(episode_number))
    if not episode_icon_name:
        logger.debug("Uploading image for episode...")
        episode_icon_name = upload_image_to_wiki(client, url, episode_number)

    return EpisodeImage(url, episode_icon_name)
