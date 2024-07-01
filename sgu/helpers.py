from typing import TYPE_CHECKING

import feedparser

from sgu.config import RSS_URL
from sgu.custom_types import PodcastEpisode

if TYPE_CHECKING:
    import requests

    from sgu.custom_types import PodcastFeedEntry


def get_podcast_episodes(feed_entries: list["PodcastFeedEntry"]) -> list[PodcastEpisode]:
    print("Getting all episodes from feed entries...")
    podcast_episodes: list[PodcastEpisode] = []
    for entry in feed_entries:
        episode_number = int(entry["link"].split("/")[-1])

        if episode_number <= 0:
            print(f"Skipping episode due to number: {entry['title']}")
            continue

        podcast_episodes.append(
            PodcastEpisode(
                episode_number=episode_number,
                download_url=entry["links"][0]["href"],
            )
        )

    return podcast_episodes


def get_rss_feed_entries(client: "requests.Session") -> list["PodcastFeedEntry"]:
    print("Getting RSS feed entries...")
    response = client.get(RSS_URL, timeout=10)
    response.raise_for_status()
    rss_content = response.text

    return feedparser.parse(rss_content)["entries"]
