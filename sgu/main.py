import requests
from dotenv import load_dotenv

from sgu.config import CUSTOM_HEADERS
from sgu.helpers import (
    convert_feed_to_episodes,
    get_rss_feed_entries,
    get_wiki_page,
)
from sgu.show_notes import get_show_notes

load_dotenv()


def main() -> None:
    print("Starting...")

    with requests.Session() as client:
        client.headers.update(CUSTOM_HEADERS)

        print("Getting RSS feed entries...")
        feed_entries = get_rss_feed_entries(client)
        episodes = convert_feed_to_episodes(feed_entries)
        episodes = sorted(episodes, key=lambda episode: episode.episode_number, reverse=True)

        for episode in episodes:
            print("Checking for wiki page...")
            wiki_page = get_wiki_page(client, episode.episode_number)

            if wiki_page:
                print("Episode has a wiki page.")
                break

            print("Getting show notes...")
            show_notes = get_show_notes(client, episode.link)

            print(show_notes)

        print("Shutting down.")


if __name__ == "__main__":
    main()
