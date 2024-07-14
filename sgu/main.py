import asyncio

import requests
from dotenv import load_dotenv

from sgu.audio_metadata import get_lyrics_from_mp3
from sgu.config import AUDIO_FOLDER, CUSTOM_HEADERS
from sgu.downloader import FileDownloader
from sgu.rss_feed import PodcastEpisode, get_podcast_episodes
from sgu.show_notes import get_data_from_show_notes
from sgu.transcription import create_transcript
from sgu.wiki import has_wiki_page

load_dotenv()


async def main() -> None:
    print("Starting...")

    with requests.Session() as client:
        client.headers.update(CUSTOM_HEADERS)

        print("Getting episodes from RSS feed...")
        podcast_episoes = get_podcast_episodes(client)

        for podcast_episode in podcast_episoes:
            print(f"Processing episode #{podcast_episode.episode_number}")

            print("Checking for wiki page...")
            wiki_page_exists = has_wiki_page(client, podcast_episode.episode_number)

            if wiki_page_exists:
                print("Episode has a wiki page. Stopping.")
                break

            wiki_page = await create_podcast_wiki_page(client, podcast_episode)

            del wiki_page  # TODO: Create this wiki page

            break  # TODO: Maybe remove this at some point. It's just making sure that we don't process multiple episodes

        print("Shutting down.")


async def create_podcast_wiki_page(client: requests.Session, podcast: PodcastEpisode) -> None:
    print("Getting show notes...")
    show_notes = get_data_from_show_notes(client, podcast.link)

    audio_file = AUDIO_FOLDER / f"{podcast.episode_number}.mp3"
    if audio_file.exists():
        audio = audio_file.read_bytes()
    else:
        print("Downloading episode...")
        downloader = FileDownloader(client)
        audio = downloader.download(podcast.download_url)
        audio_file.write_bytes(audio)

    lyrics = get_lyrics_from_mp3(audio)

    transcript = await create_transcript(audio_file, podcast)

    # TODO: Combine podcast info, show notes, lyrics data, and transcript
    del podcast, show_notes, lyrics, transcript

    # TODO: divide the transcript into segments / add the transcript text to the segments


if __name__ == "__main__":
    asyncio.run(main())
