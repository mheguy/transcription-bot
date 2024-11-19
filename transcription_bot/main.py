import sys
import time

import sentry_sdk
from sentry_sdk.crons import monitor

from transcription_bot.config import ENVIRONMENT, UNPROCESSABLE_EPISODES, config
from transcription_bot.converters.episode_data_to_segments import convert_episode_data_to_episode_segments
from transcription_bot.data_gathering import gather_data
from transcription_bot.global_http_client import http_client
from transcription_bot.global_logger import init_logging, logger
from transcription_bot.parsers.rss_feed import get_podcast_episodes
from transcription_bot.wiki import create_podcast_wiki_page, episode_has_wiki_page

sentry_sdk.init(traces_sample_rate=1.0, environment=ENVIRONMENT)


@monitor(monitor_slug="transcription-bot")
def main(*, selected_episode: int) -> None:
    """Main function that starts the program and processes podcast episodes.

    This function retrieves podcast episodes from an RSS feed,
    checks if each episode has a wiki page,
    and creates a wiki page for episodes that don't have one.
    """
    init_logging()
    config.validators.validate_all()

    logger.info("Getting episodes from RSS feed...")
    all_episodes = get_podcast_episodes(http_client)

    if selected_episode:
        allow_page_editing = True
        podcast_episode = next(episode for episode in all_episodes if episode.episode_number == selected_episode)
    else:
        allow_page_editing = False
        podcast_episode = all_episodes[0]

    logger.info(f"Selected episode #{podcast_episode.episode_number}")

    if podcast_episode.episode_number in UNPROCESSABLE_EPISODES:
        logger.error(f"Unable to process episode {podcast_episode.episode_number}. See UNPROCESSABLE_EPISODES.")
        return

    logger.info("Checking for wiki page...")
    if episode_has_wiki_page(http_client, podcast_episode.episode_number) and not allow_page_editing:
        logger.info("Episode has a wiki page. Stopping.")
        return

    logger.debug("Gathering all data...")
    episode_data = gather_data(podcast_episode, http_client)

    logger.debug("Converting data to segments...")
    episode_segments = convert_episode_data_to_episode_segments(episode_data)

    create_podcast_wiki_page(
        client=http_client,
        episode_data=episode_data,
        episode_segments=episode_segments,
        allow_page_editing=allow_page_editing,
    )

    logger.success(f"Episode #{podcast_episode.episode_number} processed.")
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

    # Sleep to allow sentry to flush
    time.sleep(5)
