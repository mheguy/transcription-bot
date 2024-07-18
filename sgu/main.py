import asyncio

import requests
from dotenv import load_dotenv

from sgu.config import CUSTOM_HEADERS
from sgu.data_gathering import gather_data
from sgu.rss_feed import PodcastEpisode, get_podcast_episodes
from sgu.wiki import has_wiki_page

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
            wiki_page_exists = has_wiki_page(client, podcast_episode.episode_number)

            if wiki_page_exists:
                print("Episode has a wiki page. Stopping.")
                break

            wiki_page = await create_podcast_wiki_page(client, podcast_episode)

            del wiki_page  # TODO: Create this wiki page

            break  # TODO: Maybe remove this at some point. It's just making sure that we don't process multiple episodes

        print("Shutting down.")


async def create_podcast_wiki_page(client: requests.Session, podcast: PodcastEpisode) -> None:
    # Gather all data
    print("Gathering all data...")
    episode_data = await gather_data(client, podcast)

    # convert episode data to segments

    # TODO: Convert the segments to a wiki page


if __name__ == "__main__":
    asyncio.run(main())
