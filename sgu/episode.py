from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from sgu.segments import get_segments

if TYPE_CHECKING:
    from time import struct_time

    from sgu.segments import BaseSegment


@dataclass
class PodcastEpisode:
    episode_number: int
    official_title: str
    summary: str
    download_url: str
    link: str
    segments: list["BaseSegment"]
    published_time: "struct_time"

    @staticmethod
    def from_feed_entry(feed_entry: dict[str, Any]) -> "PodcastEpisode":
        return PodcastEpisode(
            episode_number=int(feed_entry["link"].split("/")[-1]),
            official_title=feed_entry["title"],
            summary=feed_entry["summary"],
            download_url=feed_entry["links"][0]["href"],
            link=feed_entry["link"],
            segments=get_segments(feed_entry["summary"]),
            published_time=feed_entry["published_parsed"],
        )
