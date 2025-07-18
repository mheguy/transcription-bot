"""Create a transcript for a podcast episode.

If no arguments are provided, it will check for the most recent episode and process it.
"""

import sys

import cronitor
from loguru import logger

from transcription_bot.handlers.episode_data_handler import create_episode_data
from transcription_bot.handlers.episode_raw_data_handler import gather_raw_data
from transcription_bot.handlers.episode_segment_handler import extract_episode_segments_from_episode_raw_data
from transcription_bot.handlers.transcription_handler import get_transcript
from transcription_bot.interfaces.wiki import EPISODE_PAGE_PREFIX, episode_has_wiki_page, save_wiki_page
from transcription_bot.parsers.rss_feed import get_podcast_rss_entries
from transcription_bot.serializers.wiki import create_podcast_wiki_page
from transcription_bot.utils.config import UNPROCESSABLE_EPISODES, config
from transcription_bot.utils.global_http_client import http_client
from transcription_bot.utils.helpers import run_main_safely, setup_tracing

setup_tracing(config)


@cronitor.job(config.cronitor_job_id)
def main(*, selected_episode: int) -> None:
    """Create/update a transcript for an episode of the podcast.

    By default, this will transcribe the latest episode (if no wiki page exists for it).
    """
    config.validators.validate_all()

    logger.info("Getting episodes from RSS feed...")
    rss_entries = get_podcast_rss_entries(http_client)

    if selected_episode:
        allow_page_editing = True
        podcast_rss_entry = next(episode for episode in rss_entries if episode.episode_number == selected_episode)
    else:
        allow_page_editing = False
        podcast_rss_entry = rss_entries[0]

    logger.info(f"Selected episode #{podcast_rss_entry.episode_number}")

    if podcast_rss_entry.episode_number in UNPROCESSABLE_EPISODES:
        logger.error(f"Unable to process episode {podcast_rss_entry.episode_number}. See UNPROCESSABLE_EPISODES.")
        return

    logger.info("Checking for wiki page...")
    if episode_has_wiki_page(podcast_rss_entry.episode_number) and not allow_page_editing:
        logger.info("Episode has a wiki page. Stopping.")
        return

    logger.debug("Getting transcript...")
    transcript = get_transcript(podcast_rss_entry)
    if transcript is None:
        logger.info("Transcription not available. Stopping.")
        return

    logger.debug("Gathering raw data...")
    episode_raw_data = gather_raw_data(podcast_rss_entry, http_client)

    logger.debug("Converting raw data to segments...")
    episode_segments = extract_episode_segments_from_episode_raw_data(episode_raw_data)

    logger.info("Merging transcript into episode segments...")
    episode_data = create_episode_data(episode_raw_data, transcript, episode_segments)

    logger.info("Converting episode data to wiki markdown...")
    wiki_page = create_podcast_wiki_page(episode_data)

    logger.info("Creating (or updating) wiki page...")
    save_wiki_page(
        f"{EPISODE_PAGE_PREFIX}{episode_raw_data.rss_entry.episode_number}",
        wiki_page,
        allow_page_editing=allow_page_editing,
    )

    logger.success(f"Episode #{podcast_rss_entry.episode_number} processed.")
    logger.success("Shutting down.")


if __name__ == "__main__":
    _, *_episodes_to_process = sys.argv

    _episode_to_process = 0

    if _episodes_to_process:
        if len(_episodes_to_process) > 1:
            raise ValueError("Only one episode number is allowed.")
        else:
            _episode_to_process = int(_episodes_to_process[0])

    run_main_safely(main, selected_episode=_episode_to_process)
