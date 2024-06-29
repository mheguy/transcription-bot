from sgu_sof_tool.episodes import get_podcast_episodes, get_rss_feed_entries
from sgu_sof_tool.helpers import ensure_directories
from sgu_sof_tool.transcription import ensure_transcriptions_generated


def main() -> None:
    ensure_directories()

    feed_entries = get_rss_feed_entries()
    episodes = get_podcast_episodes(feed_entries)

    ensure_transcriptions_generated(episodes)


if __name__ == "__main__":
    main()
