from dataclasses import dataclass
from http.client import NOT_FOUND
from typing import TYPE_CHECKING

import requests
from dotenv import load_dotenv

from sgu.config import CUSTOM_HEADERS, WIKI_EPISODE_URL_BASE
from sgu.rss_feed import PodcastFeedEntry, get_rss_feed_entries
from sgu.segments import EPISODE_NUMBER, BaseSegment, create_segments
from sgu.show_notes import ShowNotesData, get_data_from_show_notes

if TYPE_CHECKING:
    from sgu.segments import BaseSegment

load_dotenv()


@dataclass
class PodcastEpisode:
    episode_number: int
    image_url: str
    segments: list["BaseSegment"]

    @staticmethod
    def from_feed_entry_and_show_notes_data(
        rss_feed_data: "PodcastFeedEntry", show_notes_data: ShowNotesData
    ) -> "PodcastEpisode":
        segments = create_segments(rss_feed_data, show_notes_data)

        return PodcastEpisode(
            episode_number=rss_feed_data.episode_number,
            image_url=show_notes_data.image_url,
            segments=segments,
        )


def has_wiki_page(client: "requests.Session", episode_number: int) -> bool:
    resp = client.get(WIKI_EPISODE_URL_BASE + str(episode_number))

    if resp.status_code == NOT_FOUND:
        return False

    resp.raise_for_status()

    return True


def main() -> None:
    print("Starting...")

    with requests.Session() as client:
        client.headers.update(CUSTOM_HEADERS)

        print("Getting episodes from RSS feed...")
        rss_feed_entries = get_rss_feed_entries(client)

        for feed_entry in rss_feed_entries:
            # TODO: Remove this debug code
            EPISODE_NUMBER["value"] = feed_entry.episode_number

            if feed_entry.episode_number > 1000:
                continue

            # TODO: Remove debug code (above)

            print(f"Processing episode #{feed_entry.episode_number}")

            # print("Checking for wiki page...")
            # wiki_page = has_wiki_page(client, feed_entry.episode_number)

            # if wiki_page:
            #     print("Episode has a wiki page. Stopping.")
            # break

            print("Getting show notes data...")
            show_notes_data = get_data_from_show_notes(client, feed_entry.link)

            episode = PodcastEpisode.from_feed_entry_and_show_notes_data(feed_entry, show_notes_data)

            print(f"Episode {episode.episode_number} complete.")

        print("Shutting down.")


if __name__ == "__main__":
    main()
