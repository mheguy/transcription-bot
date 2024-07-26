import asyncio

import requests
from dotenv import load_dotenv

from sgu.config import CUSTOM_HEADERS
from sgu.custom_logger import logger
from sgu.parsers.rss_feed import get_podcast_episodes
from sgu.wiki import create_podcast_wiki_page, episode_has_wiki_page

load_dotenv()


async def main() -> None:
    """Main function that starts the program and processes podcast episodes.

    This function retrieves podcast episodes from an RSS feed, checks if each episode has a wiki page,
    and creates a wiki page for episodes that don't have one.
    """
    logger.success("Starting...")

    with requests.Session() as client:
        client.headers.update(CUSTOM_HEADERS)

        logger.info("Getting episodes from RSS feed...")
        podcast_episoes = get_podcast_episodes(client)

        for podcast_episode in podcast_episoes:
            logger.info(f"Processing episode #{podcast_episode.episode_number}")

            logger.info("Checking for wiki page...")
            wiki_page_exists = episode_has_wiki_page(client, podcast_episode.episode_number)

            if wiki_page_exists:
                logger.info("Episode has a wiki page. Stopping.")
                break

            await create_podcast_wiki_page(client, podcast_episode)

            break  # TODO: Maybe remove this at some point. It's just making sure that we don't process multiple episodes

        logger.success("Shutting down.")


if __name__ == "__main__":
    asyncio.run(main())
