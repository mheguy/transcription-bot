import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import feedparser

from sgu.config import RSS_URL

if TYPE_CHECKING:
    from time import struct_time

    import requests


@dataclass
class PodcastEpisode:
    """Basic information about a podcast episode."""

    episode_number: int
    official_title: str
    summary: str
    download_url: str
    link: str
    published_time: "struct_time"


def get_podcast_episodes(client: "requests.Session") -> list[PodcastEpisode]:
    """Retrieve the list of SGU podcast episodes.

    Args:
        client (requests.Session): The HTTP client to use for making requests.

    Returns:
        list[PodcastEpisode]: A list of podcast episodes, sorted by episode number in descending order.
    """
    raw_feed_entries = _get_raw_rss_feed_entries(client)
    feed_entries = _convert_feed_entries_to_episodes(raw_feed_entries)
    return sorted(feed_entries, key=lambda e: e.episode_number, reverse=True)


def _get_raw_rss_feed_entries(client: "requests.Session") -> list[dict[str, Any]]:
    response = client.get(RSS_URL, timeout=10)
    response.raise_for_status()

    return feedparser.parse(response.text)["entries"]


def _convert_feed_entries_to_episodes(feed_entries: list[dict[str, Any]]) -> list[PodcastEpisode]:
    podcast_episodes: list[PodcastEpisode] = []
    for entry in feed_entries:
        episode_number = int(entry["link"].split("/")[-1])

        # Skip episodes that don't have a number.
        if episode_number <= 0:
            logging.info("Skipping episode due to number: %s", entry["title"])
            continue

        podcast_episodes.append(
            PodcastEpisode(
                episode_number=int(entry["link"].split("/")[-1]),
                official_title=entry["title"],
                summary=entry["summary"],
                download_url=entry["links"][0]["href"],
                link=entry["link"],
                published_time=entry["published_parsed"],
            )
        )

    return podcast_episodes
