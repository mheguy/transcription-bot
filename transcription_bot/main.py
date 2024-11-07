import sys

import cronitor
import sentry_sdk

from transcription_bot.config import CRONITOR_API_KEY, CRONITOR_JOB_KEY, SENTRY_DSN, UNPROCESSABLE_EPISODES
from transcription_bot.data_gathering import gather_data
from transcription_bot.global_http_client import http_client
from transcription_bot.global_logger import logger
from transcription_bot.parsers.episode_data import convert_episode_data_to_episode_segments
from transcription_bot.parsers.rss_feed import get_podcast_episodes
from transcription_bot.transcript_formatting import adjust_transcript_for_voiceover
from transcription_bot.transcription_splitting import add_transcript_to_segments
from transcription_bot.wiki import create_podcast_wiki_page, episode_has_wiki_page

sentry_sdk.init(dsn=SENTRY_DSN, traces_sample_rate=1.0)


def main(*, allow_page_editing: bool, inputs: list[str]) -> None:
    """Main function that starts the program and processes podcast episodes.

    This function retrieves podcast episodes from an RSS feed,
    checks if each episode has a wiki page,
    and creates a wiki page for episodes that don't have one.
    """
    cronitor.api_key = CRONITOR_API_KEY
    monitor = cronitor.Monitor(CRONITOR_JOB_KEY)
    logger.info("Getting episodes from RSS feed...")
    podcast_episodes = get_podcast_episodes(http_client)

    if inputs:
        if len(inputs) > 1:
            raise ValueError("Only one episode number is allowed.")

        episode_number = int(inputs[0])
        podcast_episode = next(episode for episode in podcast_episodes if episode.episode_number == episode_number)
    else:
        podcast_episode = podcast_episodes[0]

    logger.info(f"Processing episode #{podcast_episode.episode_number}")

    if podcast_episode.episode_number in UNPROCESSABLE_EPISODES:
        logger.info(f"Unable to process episode {podcast_episode.episode_number}. See UNPROCESSABLE_EPISODES.")
        return

    logger.info("Checking for wiki page...")
    if not allow_page_editing and episode_has_wiki_page(http_client, podcast_episode.episode_number):
        logger.info("Episode has a wiki page. Stopping.")
        monitor.ping(state="complete", metric={"count": 0})
        return

    logger.debug("Gathering all data...")
    episode_data = gather_data(podcast_episode, http_client)
    adjust_transcript_for_voiceover(episode_data.transcript)

    logger.debug("Converting data to segments...")
    episode_segments = convert_episode_data_to_episode_segments(episode_data)

    logger.debug("Merging transcript into episode segments...")
    episode_segments = add_transcript_to_segments(episode_data.podcast, episode_data.transcript, episode_segments)

    create_podcast_wiki_page(
        client=http_client,
        episode_data=episode_data,
        episode_segments=episode_segments,
        allow_page_editing=allow_page_editing,
    )

    logger.success(f"Episode #{podcast_episode.episode_number} processed.")
    monitor.ping(state="complete", metric={"count": 1})
    logger.success("Shutting down.")


if __name__ == "__main__":
    _, *episodes_to_process = sys.argv

    main(
        allow_page_editing=False,
        inputs=episodes_to_process,
    )
