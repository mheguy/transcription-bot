"""Create a transcript for a podcast episode.

If no arguments are provided, it will check for the most recent episode and process it.
"""

import sys
import time

import cronitor
import sentry_sdk

from transcription_bot.config import UNPROCESSABLE_EPISODES, config
from transcription_bot.converters.episode_data_to_segments import (
    add_transcript_to_segments,
    convert_episode_data_to_episode_segments,
)
from transcription_bot.data_gathering import gather_metadata
from transcription_bot.global_http_client import http_client
from transcription_bot.global_logger import init_logging, logger
from transcription_bot.parsers.rss_feed import get_podcast_rss_entries
from transcription_bot.transcription import get_transcript
from transcription_bot.wiki import create_podcast_wiki_page, episode_has_wiki_page

if not config.local_mode:
    sentry_sdk.init(dsn=config.sentry_dsn, environment="production")
    cronitor.api_key = config.cronitor_api_key


@cronitor.job(config.cronitor_job_id)
def main(*, selected_episode: int) -> None:
    """Create/update a transcript for an episode of the podcast.

    By default, this will transcribe the latest episode (if no wiki page exists for it).
    """
    init_logging()
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
    if episode_has_wiki_page(http_client, podcast_rss_entry.episode_number) and not allow_page_editing:
        logger.info("Episode has a wiki page. Stopping.")
        return

    logger.debug("Gathering all data...")
    episode_metadata = gather_metadata(podcast_rss_entry, http_client)
    transcript = get_transcript(podcast_rss_entry)

    logger.debug("Converting data to segments...")
    episode_segments = convert_episode_data_to_episode_segments(episode_metadata)

    logger.info("Merging transcript into episode segments...")
    transcribed_segments = add_transcript_to_segments(episode_metadata.podcast, transcript, episode_segments)
    # TODO: Enable this
    # transcribed_segments = enhance_transcribed_segments(podcast_rss_entry, transcribed_segments)

    logger.info("Creating wiki page...")
    create_podcast_wiki_page(
        client=http_client,
        episode_data=episode_metadata,
        episode_segments=transcribed_segments,
        allow_page_editing=allow_page_editing,
        rogues={s["speaker"].lower() for s in transcript},
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

    main(selected_episode=_episode_to_process)

    # Sleep to allow monitors to flush
    time.sleep(5)

    logger.info("Exiting clean.")
