import sys

import sentry_sdk
from sentry_sdk.crons import monitor

from transcription_bot.config import ENVIRONMENT, UNPROCESSABLE_EPISODES
from transcription_bot.converters.episode_data_to_segments import convert_episode_data_to_episode_segments
from transcription_bot.data_gathering import gather_data
from transcription_bot.global_http_client import http_client
from transcription_bot.global_logger import logger
from transcription_bot.parsers.rss_feed import get_podcast_episodes
from transcription_bot.wiki import create_podcast_wiki_page, episode_has_wiki_page

sentry_sdk.init(traces_sample_rate=1.0, environment=ENVIRONMENT)


@monitor(monitor_slug="transcription-bot")
def main(*, allow_page_editing: bool, selected_episodes: list[str]) -> None:
    """Main function that starts the program and processes podcast episodes.

    This function retrieves podcast episodes from an RSS feed,
    checks if each episode has a wiki page,
    and creates a wiki page for episodes that don't have one.
    """
    logger.info("Getting episodes from RSS feed...")
    all_episodes = get_podcast_episodes(http_client)

    if selected_episodes:
        if len(selected_episodes) > 1:
            raise ValueError("Only one episode number is allowed.")

        episode_number = int(selected_episodes[0])
        podcast_episode = next(episode for episode in all_episodes if episode.episode_number == episode_number)
    else:
        podcast_episode = all_episodes[0]

    logger.info(f"Processing episode #{podcast_episode.episode_number}")

    if podcast_episode.episode_number in UNPROCESSABLE_EPISODES:
        logger.info(f"Unable to process episode {podcast_episode.episode_number}. See UNPROCESSABLE_EPISODES.")
        return

    logger.info("Checking for wiki page...")
    if not allow_page_editing and episode_has_wiki_page(http_client, podcast_episode.episode_number):
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

    main(
        allow_page_editing=False,
        selected_episodes=_episodes_to_process,
    )
