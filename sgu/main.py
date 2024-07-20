import asyncio

import requests
from dotenv import load_dotenv

from sgu.config import CUSTOM_HEADERS
from sgu.parsers.rss_feed import get_podcast_episodes
from sgu.wiki import create_podcast_wiki_page, episode_has_wiki_page

load_dotenv()


async def main() -> None:
    """Main function that starts the program and processes podcast episodes.

    This function retrieves podcast episodes from an RSS feed, checks if each episode has a wiki page,
    and creates a wiki page for episodes that don't have one.
    """
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

            await create_podcast_wiki_page(client, podcast_episode)

            break  # TODO: Maybe remove this at some point. It's just making sure that we don't process multiple episodes

        print("Shutting down.")


if __name__ == "__main__":
    asyncio.run(main())
