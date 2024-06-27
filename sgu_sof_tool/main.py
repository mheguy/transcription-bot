from sgu_sof_tool.episodes import get_podcast_episodes, get_rss_feed_entries
from sgu_sof_tool.helpers import ensure_directories


def main() -> None:
    ensure_directories()

    feed_entries = get_rss_feed_entries()
    episodes = get_podcast_episodes(feed_entries)


if __name__ == "__main__":
    main()
