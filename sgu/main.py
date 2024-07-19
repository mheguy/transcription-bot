import asyncio
from typing import TYPE_CHECKING

import requests
from dotenv import load_dotenv

from sgu.config import CUSTOM_HEADERS
from sgu.data_gathering import gather_data
from sgu.parsers.lyrics import parse_lyrics
from sgu.parsers.rss_feed import PodcastEpisode, get_podcast_episodes
from sgu.parsers.show_notes import get_episode_image, parse_show_notes
from sgu.parsers.summary_text import parse_summary_text
from sgu.segment_joiner import join_segments
from sgu.wiki import convert_to_wiki, edit_page, episode_has_wiki_page, log_into_wiki

if TYPE_CHECKING:
    from sgu.data_gathering import EpisodeData
    from sgu.segment_types import Segments

load_dotenv()


async def main() -> None:
    print("Starting...")

    with requests.Session() as client:
        client.headers.update(CUSTOM_HEADERS)

        print("Getting episodes from RSS feed...")
        podcast_episoes = get_podcast_episodes(client)

        for podcast_episode in podcast_episoes:
            print(f"Processing episode #{podcast_episode.episode_number}")

            print("Checking for wiki page...")
            wiki_page_exists = episode_has_wiki_page(client, podcast_episode.episode_number)

            if wiki_page_exists:
                print("Episode has a wiki page. Stopping.")
                break

            wiki_page = await create_podcast_wiki_page(client, podcast_episode)

            csrf_token = log_into_wiki(client)
            edit_page(client, csrf_token, page_text=wiki_page)

            break  # TODO: Maybe remove this at some point. It's just making sure that we don't process multiple episodes

        print("Shutting down.")


async def create_podcast_wiki_page(client: requests.Session, podcast: PodcastEpisode) -> str:
    # Gather all data
    print("Gathering all data...")
    episode_data = await gather_data(client, podcast)

    print("Merging data...")
    segments = convert_episode_data_to_segments(episode_data)
    episode_image = get_episode_image(episode_data.show_notes)

    print("Creating wiki page...")
    return convert_to_wiki(episode_data, segments, episode_image)


def convert_episode_data_to_segments(episode_data: "EpisodeData") -> "Segments":
    lyric_segments = parse_lyrics(episode_data.lyrics)
    show_note_segments = parse_show_notes(episode_data.show_notes)
    summary_text_segments = parse_summary_text(episode_data.podcast.summary)

    return join_segments(lyric_segments, show_note_segments, summary_text_segments)


if __name__ == "__main__":
    asyncio.run(main())
