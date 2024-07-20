import os
from http.client import NOT_FOUND
from typing import TYPE_CHECKING

from sgu.config import WIKI_API_BASE, WIKI_EPISODE_URL_BASE
from sgu.data_gathering import gather_data
from sgu.parsers.episode_data import convert_episode_data_to_segments
from sgu.parsers.show_notes import get_episode_image_url

if TYPE_CHECKING:
    from requests import Session

    from sgu.data_gathering import EpisodeData
    from sgu.parsers.rss_feed import PodcastEpisode
    from sgu.segment_types import Segments
    from sgu.transcription import DiarizedTranscript


async def create_podcast_wiki_page(client: "Session", podcast: "PodcastEpisode"):
    """Creates a wiki page for a podcast episode.

    This function gathers all the necessary data for the episode, merges the data into segments,
    and converts the segments into wiki page content.

    Args:
        client (requests.Session): The HTTP client session.
        podcast (PodcastEpisode): The podcast episode.

    Returns:
        str: The wiki page content.
    """
    # Gather all data
    print("Gathering all data...")
    episode_data = await gather_data(client, podcast)

    print("Merging data...")
    segments = convert_episode_data_to_segments(episode_data)
    episode_image = get_episode_image_url(episode_data.show_notes)

    print("Creating wiki page...")
    wiki_page = _convert_to_wiki(episode_data, segments, episode_image)

    _edit_page(client, page_text=wiki_page)  # TODO: Change for "Craete page"


def episode_has_wiki_page(client: "Session", episode_number: int) -> bool:
    """Check if an episode has a wiki page.

    Args:
        client (Session): The HTTP client session.
        episode_number (int): The episode number.

    Returns:
        bool: True if the episode has a wiki page, False otherwise.
    """
    resp = client.get(WIKI_EPISODE_URL_BASE + str(episode_number))

    if resp.status_code == NOT_FOUND:
        return False

    resp.raise_for_status()

    return True


def _convert_to_wiki(episode_data: "EpisodeData", segments: "Segments", episode_image: str) -> str:
    components = [
        f"Episode #{episode_data.podcast.episode_number}",
        f"Title: {episode_data.podcast.official_title}",
        f"Download URL: {episode_data.podcast.download_url}",
        f"Link: {episode_data.podcast.link}",
        f"Episode Image (link): {episode_image}",
        ("Segments:\n\n" + "\n\n".join(str(s) for s in segments)),
        f"Transcript:\n\n{_convert_transcript_to_text(episode_data.transcript)}",
    ]

    return "\n\n\n\n".join(components)


def _convert_transcript_to_text(transcript: "DiarizedTranscript") -> str:
    text_segments: list[str] = []
    for segment in transcript:
        start_time = "{:02d}:{:02d}:{:02d}".format(
            int(segment["start"]) // 3600,
            int(segment["start"]) // 60 % 60,
            int(segment["start"]) % 60,
        )

        text = f"{start_time}-{segment['speaker']}<br>{segment['text']}"
        text_segments.append(text)

    return "\n\n".join(text_segments)


def _edit_page(client: "Session", page_title: str = "User:Mheguy", page_text: str = "") -> None:
    csrf_token = _log_into_wiki(client)

    payload = {
        "action": "edit",
        "title": page_title,
        "format": "json",
        "text": page_text,
        "notminor": True,
        "bot": True,
        "nocreate": True,
        "token": csrf_token,
    }

    resp = client.post(WIKI_API_BASE, data=payload)
    resp.raise_for_status()
    data = resp.json()

    print(data)


def _log_into_wiki(client: "Session") -> str:
    login_token = _get_login_token(client)
    _send_credentials(client, login_token)

    return _get_csrf_token(client)


def _get_login_token(client: "Session") -> str:
    params = {"action": "query", "meta": "tokens", "type": "login", "format": "json"}

    resp = client.get(url=WIKI_API_BASE, params=params)
    resp.raise_for_status()
    data = resp.json()

    return data["query"]["tokens"]["logintoken"]


def _send_credentials(client: "Session", login_token: str) -> None:
    payload = {
        "action": "login",
        "lgname": "Mheguy@mheguy-transcription-bot",
        "lgpassword": os.environ["WIKI_PASS"],
        "lgtoken": login_token,
        "format": "json",
    }

    resp = client.post(WIKI_API_BASE, data=payload)
    resp.raise_for_status()

    if not resp.json()["login"]["result"] == "Success":
        raise ValueError("Login failed")


def _get_csrf_token(client: "Session") -> str:
    params = {"action": "query", "meta": "tokens", "format": "json"}

    resp = client.get(url=WIKI_API_BASE, params=params)
    resp.raise_for_status()
    data = resp.json()

    return data["query"]["tokens"]["csrftoken"]
