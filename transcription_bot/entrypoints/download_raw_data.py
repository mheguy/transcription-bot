"""Download the raw data for a range of episodes."""

from concurrent.futures import ThreadPoolExecutor

from loguru import logger

from transcription_bot.handlers.episode_raw_data_handler import gather_raw_data
from transcription_bot.models.data_models import PodcastRssEntry
from transcription_bot.parsers.rss_feed import get_podcast_rss_entries
from transcription_bot.utils.config import config
from transcription_bot.utils.global_http_client import http_client
from transcription_bot.utils.helpers import run_main_safely

logger.debug("Imports completed.")


def main(episode_numbers: set[int]) -> None:
    """Download raw data."""
    logger.info("Validating config...")
    config.validators.validate_all()

    if not episode_numbers:
        logger.info("No episode numbers provided. Exiting.")
        return

    logger.info("Getting episodes from podcast RSS feed...")
    rss_map = {episode.episode_number: episode for episode in get_podcast_rss_entries(http_client)}
    rss_map = {episode_number: rss_map[episode_number] for episode_number in episode_numbers}

    logger.info(f"Processing {len(rss_map)} episodes...")

    def process_episode(episode_number: int, podcast_rss_entry: PodcastRssEntry) -> None:
        logger.info(f"Processing episode #{episode_number}")
        gather_raw_data(podcast_rss_entry, http_client)

    with ThreadPoolExecutor(max_workers=5) as executor:
        for episode_number, podcast_rss_entry in rss_map.items():
            executor.submit(process_episode, episode_number, podcast_rss_entry)


if __name__ == "__main__":
    logger.info("Starting...")
    _episodes_to_process = set(range(0))
    run_main_safely(main, _episodes_to_process)
