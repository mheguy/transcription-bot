import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import TYPE_CHECKING

import feedparser
import requests

from sgu_sof_tool.config import CONCURRENT_DOWNLOAD_LIMIT, RSS_URL
from sgu_sof_tool.constants import DATA_FOLDER, EPISODE_FOLDER
from sgu_sof_tool.custom_types import PodcastFeedEntry

if TYPE_CHECKING:
    from pathlib import Path

    from sgu_sof_tool.custom_types import PodcastFeedEntry

RSS_FILE = DATA_FOLDER / "rss.xml"
SIX_DAYS = 60 * 60 * 24 * 6
FILE_SIZE_CUTOFF = 100_000


@dataclass
class Episode:
    episode_number: int
    download_url: str
    file: "Path"
    expected_file_size: int

    def __post_init__(self) -> None:
        if self.file.exists() and self.file.stat().st_size < FILE_SIZE_CUTOFF:
            raise RuntimeError(f"File size too small for episode #{self.episode_number}")


def get_podcast_episodes(feed_entries: list["PodcastFeedEntry"]) -> list[Episode]:
    podcast_episodes: list[Episode] = []
    for entry in feed_entries:
        episode_number = int(entry["link"].split("/")[-1])

        if episode_number <= 0:
            print(f"Skipping episode due to number: {entry['title']}")
            continue

        podcast_episodes.append(
            Episode(
                episode_number=episode_number,
                download_url=entry["links"][0]["href"],
                file=EPISODE_FOLDER / f"{episode_number:04}.mp3",
                expected_file_size=int(entry["links"][0]["length"]),
            )
        )

    podcasts_to_download = [episode for episode in podcast_episodes if not episode.file.exists()]
    download_podcast_episodes(podcasts_to_download)

    return podcast_episodes


def download_podcast_episodes(episodes: list[Episode]) -> None:
    """Downloads a batch of podcast episodes."""
    with ThreadPoolExecutor(max_workers=CONCURRENT_DOWNLOAD_LIMIT) as executor:
        futures = [executor.submit(download_file, episode) for episode in episodes]
        for f in futures:
            f.result()


def download_file(episode: Episode) -> None:
    print(f"Downloading episode: {episode.episode_number}")

    resp = requests.get(episode.download_url, timeout=3600)
    resp.raise_for_status()
    episode.file.write_bytes(resp.content)

    if episode.file.stat().st_size < FILE_SIZE_CUTOFF:
        raise RuntimeError(f"File size too small for episode #{episode.episode_number}")


def get_rss_feed_entries() -> list["PodcastFeedEntry"]:
    if RSS_FILE.exists() and time.time() - SIX_DAYS < RSS_FILE.stat().st_mtime:
        rss_content = RSS_FILE.read_text()
    else:
        response = requests.get(RSS_URL, timeout=10)
        response.raise_for_status()
        rss_content = response.text
        RSS_FILE.parent.mkdir(parents=True, exist_ok=True)
        RSS_FILE.write_text(rss_content)

    return feedparser.parse(rss_content)["entries"]
