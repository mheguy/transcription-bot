import requests
from dotenv import load_dotenv

from sgu.helpers import (
    get_podcast_episodes,
    get_rss_feed_entries,
)

load_dotenv()


def main() -> None:
    print("Starting...")

    with requests.Session() as client:
        feed_entries = get_rss_feed_entries(client)
        episodes = get_podcast_episodes(feed_entries)

        for episode in episodes:
            ...


if __name__ == "__main__":
    main()
