import logging
from http.client import NOT_FOUND
from typing import TYPE_CHECKING, Any

import feedparser

from sgu.config import RSS_URL, WIKI_EPISODE_URL_BASE
from sgu.episode import PodcastEpisode

if TYPE_CHECKING:
    import requests


def convert_feed_to_episodes(feed_entries: list[dict[str, Any]]) -> list[PodcastEpisode]:
    logging.debug("Getting all episodes from feed entries...")
    podcast_episodes: list[PodcastEpisode] = []
    for entry in feed_entries:
        episode_number = int(entry["link"].split("/")[-1])

        # Skip episodes that don't have a number.
        if episode_number <= 0:
            logging.info("Skipping episode due to number: %s", entry["title"])
            continue

        podcast_episodes.append(PodcastEpisode.from_feed_entry(entry))

    return podcast_episodes


def get_rss_feed_entries(client: "requests.Session") -> list[dict[str, Any]]:
    logging.debug("Getting RSS feed entries...")
    response = client.get(RSS_URL, timeout=10)
    response.raise_for_status()

    return feedparser.parse(response.text)["entries"]


def get_wiki_page(client: "requests.Session", episode_number: int) -> Any | None:
    resp = client.get(WIKI_EPISODE_URL_BASE + str(episode_number))

    if resp.status_code == NOT_FOUND:
        return None

    resp.raise_for_status()

    return resp
