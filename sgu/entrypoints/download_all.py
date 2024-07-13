import asyncio
from pathlib import Path

import httpx
import requests

from sgu.downloader import Mp3Downloader
from sgu.rss_feed import get_rss_feed_entries

EPISODES_FOLDER = Path("data/episodes").resolve()


async def main() -> None:
    downloaded_episodes = {int(f.stem) for f in EPISODES_FOLDER.glob("*.mp3")}

    with requests.Session() as sync_client:
        rss_entries = get_rss_feed_entries(sync_client)

    missing_episodes = [e for e in rss_entries if e.episode_number not in downloaded_episodes]

    print("Total episodes:", len(rss_entries))
    print("Downloaded episodes:", len(downloaded_episodes))
    print("Missing episodes:", len(missing_episodes))

    limits = httpx.Limits(max_keepalive_connections=3, max_connections=5)
    async with httpx.AsyncClient(timeout=120, follow_redirects=True, limits=limits) as async_client:
        downloader = Mp3Downloader(async_client)

        tasks = [asyncio.ensure_future(downloader.download_async(episode.download_url)) for episode in missing_episodes]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for episode, result in zip(missing_episodes, results, strict=False):
            if isinstance(result, bytes):
                print(f"Downloaded episode #{episode.episode_number}")
                (EPISODES_FOLDER / f"{episode.episode_number:04}.mp3").write_bytes(result)
                continue

            print(f"Failed to download episode #{episode.episode_number}: {result}")

    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())