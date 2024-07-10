from dataclasses import dataclass
from typing import TYPE_CHECKING

import requests
from dotenv import load_dotenv

from sgu.audio_metadata import LyricsData, process_mp3
from sgu.config import CUSTOM_HEADERS
from sgu.downloader import Mp3Downloader
from sgu.rss_feed import PodcastFeedEntry, get_rss_feed_entries
from sgu.segments import BaseSegment, create_segments
from sgu.show_notes import ShowNotesData, get_data_from_show_notes
from sgu.wiki import has_wiki_page

if TYPE_CHECKING:
    from sgu.segments import BaseSegment

load_dotenv()


@dataclass
class PodcastEpisode:
    episode_number: int
    image_url: str
    segments: list["BaseSegment"]

    @staticmethod
    def combine_data_streams(
        rss_feed_data: "PodcastFeedEntry",
        show_notes_data: ShowNotesData,
        lyric_data: LyricsData,
    ) -> "PodcastEpisode":
        segments = create_segments(rss_feed_data, show_notes_data)

        return PodcastEpisode(
            episode_number=rss_feed_data.episode_number,
            image_url=show_notes_data.image_url,
            segments=segments,
        )


def main() -> None:
    print("Starting...")

    with requests.Session() as client:
        client.headers.update(CUSTOM_HEADERS)

        print("Getting episodes from RSS feed...")
        rss_feed_entries = get_rss_feed_entries(client)

        for feed_entry in rss_feed_entries:
            print(f"Processing episode #{feed_entry.episode_number}")

            print("Checking for wiki page...")
            wiki_page = has_wiki_page(client, feed_entry.episode_number)

            if wiki_page:
                print("Episode has a wiki page. Stopping.")
                break

            print("Getting show notes data...")
            show_notes_data = get_data_from_show_notes(client, feed_entry.link)

            print("Downloading episode...")
            downloader = Mp3Downloader(client)
            audio = downloader.download(feed_entry.download_url)

            lyrics_data = process_mp3(audio)

            episode = PodcastEpisode.combine_data_streams(feed_entry, show_notes_data, lyrics_data)

            print(f"Episode {episode.episode_number} complete.")

        print("Shutting down.")


if __name__ == "__main__":
    main()
