import asyncio

from dotenv import load_dotenv

from sgu.data_gathering import gather_data
from sgu.global_http_client import http_client
from sgu.global_logger import logger
from sgu.parsers.episode_data import convert_episode_data_to_episode_segments
from sgu.parsers.rss_feed import get_podcast_episodes
from sgu.transcript_formatting import adjust_transcript_for_voiceover
from sgu.transcription_splitting import add_transcript_to_segments
from sgu.wiki import create_podcast_wiki_page, episode_has_wiki_page

load_dotenv()


async def main() -> None:
    """Main function that starts the program and processes podcast episodes.

    This function retrieves podcast episodes from an RSS feed,
    checks if each episode has a wiki page,
    and creates a wiki page for episodes that don't have one.
    """
    logger.success("Starting...")

    logger.info("Getting episodes from RSS feed...")
    podcast_episoes = get_podcast_episodes(http_client)

    for podcast_episode in podcast_episoes:
        logger.info(f"Processing episode #{podcast_episode.episode_number}")

        logger.info("Checking for wiki page...")
        wiki_page_exists = episode_has_wiki_page(http_client, podcast_episode.episode_number)

        if wiki_page_exists:
            logger.info("Episode has a wiki page. Stopping.")
            break

        logger.debug("Gathering all data...")
        episode_data = await gather_data(http_client, podcast_episode)
        adjust_transcript_for_voiceover(episode_data.transcript)

        logger.debug("Converting data to segments...")
        episode_segments = convert_episode_data_to_episode_segments(episode_data)

        logger.debug("Merging transcript into episode segments...")
        episode_segments = add_transcript_to_segments(episode_data.transcript, episode_segments)

        await create_podcast_wiki_page(http_client, episode_data, episode_segments)

    logger.success("Shutting down.")


if __name__ == "__main__":
    asyncio.run(main())
