import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

import feedparser

from transcription_bot.config import config
from transcription_bot.global_logger import logger

if TYPE_CHECKING:
    from time import struct_time

    from requests import Session

EPISODE_PATTERN = r"^SGU Episode (\d{1,4})$"


@dataclass
class PodcastRssEntry:
    """Basic information about a podcast episode."""

    episode_number: int
    official_title: str
    summary: str
    download_url: str
    episode_url: str
    published_time: "struct_time"


def get_podcast_rss_entries(client: "Session") -> list[PodcastRssEntry]:
    """Retrieve the list of SGU podcast episodes from  the RSS feed."""
    response = client.get(config.podcast_rss_url, timeout=10)
    response.raise_for_status()

    raw_feed_entries = feedparser.parse(response.text)["entries"]

    feed_entries: list[PodcastRssEntry] = []
    for entry in raw_feed_entries:
        episode_number = int(entry["link"].split("/")[-1])

        # Skip episodes that don't have a number.
        if episode_number <= 0:
            logger.info("Skipping episode due to number: %s", entry["title"])
            continue

        feed_entries.append(
            PodcastRssEntry(
                episode_number=int(entry["link"].split("/")[-1]),
                official_title=entry["title"],
                summary=entry["summary"],
                download_url=entry["links"][0]["href"],
                episode_url=entry["link"],
                published_time=entry["published_parsed"],
            )
        )

    return sorted(feed_entries, key=lambda e: e.episode_number, reverse=True)


def get_recently_modified_episode_pages(client: "Session") -> set[int]:
    """Retrieve the list of recently modified episode transcripts."""
    response = client.get(config.wiki_rss_url, timeout=10)
    response.raise_for_status()

    episode_numbers: list[int] = []

    for rss_entry in feedparser.parse(response.text)["entries"]:
        match = re.match(EPISODE_PATTERN, rss_entry["title"])
        if not match:
            continue

        episode_number = int(match.group(1))
        episode_numbers.append(episode_number)

    return set(episode_numbers)
