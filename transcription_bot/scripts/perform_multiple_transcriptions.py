from transcription_bot.data_gathering import get_audio_file
from transcription_bot.global_http_client import http_client
from transcription_bot.global_logger import logger
from transcription_bot.parsers.rss_feed import get_podcast_episodes
from transcription_bot.transcription import perform_transcription
from transcription_bot.wiki import episode_has_wiki_page

EPISODES_TO_PROCESS = [
    728,
    727,
    726,
    725,
    *range(704, 723),
    *range(692, 702),
    689,
    688,
    *range(670, 686),
]


def main(episodes_to_process: list[int]) -> None:
    """Perform transcriptions of multiple episodes."""
    logger.info("Getting episodes from RSS feed...")
    podcast_episodes = get_podcast_episodes(http_client)

    podcast_episodes = [episode for episode in podcast_episodes if episode.episode_number in episodes_to_process]

    for podcast_episode in podcast_episodes:
        if episode_has_wiki_page(http_client, podcast_episode.episode_number):
            continue

        logger.info(f"Transcribing episode #{podcast_episode.episode_number}")
        audio_file = get_audio_file(http_client, podcast_episode)
        perform_transcription(podcast_episode, audio_file)


if __name__ == "__main__":
    main(EPISODES_TO_PROCESS)
