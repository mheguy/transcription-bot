import re
from datetime import datetime
from typing import cast

import feedparser
from feedparser.util import FeedParserDict
from loguru import logger
from requests import Session

from transcription_bot.models.data_models import PodcastRssEntry
from transcription_bot.utils.config import config

EPISODE_PATTERN = r"^SGU Episode (\d{1,4})$"


def get_podcast_rss_entries(client: Session) -> list[PodcastRssEntry]:
    """Retrieve the list of SGU podcast episodes from  the RSS feed."""
    response = client.get(config.podcast_rss_url)

    raw_feed_entries = feedparser.parse(response.text)["entries"]

    rss_entries: list[PodcastRssEntry] = []
    for entry in raw_feed_entries:
        entry = cast("FeedParserDict", entry)
        link = cast("str", entry["link"])

        episode_number = int(link.split("/")[-1])

        # Skip episodes that don't have a number.
        if episode_number <= 0:
            logger.debug(f"Skipping episode due to number: {entry['title']}")
            continue

        raw_download_url = cast("str", entry["links"][0]["href"])

        filename: str = raw_download_url.split("/")[-1].lower()
        date_string = filename.replace("skepticast", "").replace(".mp3", "")

        try:
            time = datetime.strptime(date_string, "%Y-%m-%d")
        except ValueError:
            time = datetime.strptime(date_string, "%m-%d-%y")

        rss_entries.append(
            PodcastRssEntry(
                episode_number=int(link.split("/")[-1]),
                summary=cast("str", entry["summary"]),
                raw_download_url=raw_download_url,
                episode_url=link,
                date=time.date(),
            )
        )

    return sorted(rss_entries, key=lambda e: e.episode_number, reverse=True)


def get_recently_modified_episode_numbers(client: Session) -> set[int]:
    """Retrieve the list of recently modified episode transcripts."""
    response = client.get(config.wiki_rss_url)

    episode_numbers: list[int] = []

    for rss_entry in feedparser.parse(response.text)["entries"]:
        match = re.match(EPISODE_PATTERN, cast("str", rss_entry["title"]))
        if not match:
            continue

        episode_number = int(match.group(1))
        episode_numbers.append(episode_number)

    return set(episode_numbers)
