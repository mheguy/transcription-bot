import os
from http.client import NOT_FOUND
from typing import TYPE_CHECKING

from sgu.config import WIKI_API_BASE, WIKI_EPISODE_URL_BASE

if TYPE_CHECKING:
    from requests import Session

    from sgu.data_gathering import EpisodeData
    from sgu.segment_types import Segments
    from sgu.transcription import DiarizedTranscript


def episode_has_wiki_page(client: "Session", episode_number: int) -> bool:
    resp = client.get(WIKI_EPISODE_URL_BASE + str(episode_number))

    if resp.status_code == NOT_FOUND:
        return False

    resp.raise_for_status()

    return True


def log_into_wiki(client: "Session") -> str:
    login_token = get_login_token(client)
    send_credentials(client, login_token)

    return get_csrf_token(client)


def get_login_token(client: "Session") -> str:
    params = {"action": "query", "meta": "tokens", "type": "login", "format": "json"}

    resp = client.get(url=WIKI_API_BASE, params=params)
    resp.raise_for_status()
    data = resp.json()

    return data["query"]["tokens"]["logintoken"]


def send_credentials(client: "Session", login_token: str) -> None:
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


def get_csrf_token(client: "Session") -> str:
    params = {"action": "query", "meta": "tokens", "format": "json"}

    resp = client.get(url=WIKI_API_BASE, params=params)
    resp.raise_for_status()
    data = resp.json()

    return data["query"]["tokens"]["csrftoken"]


def edit_page(client: "Session", csrf_token: str, page_title: str = "User:Mheguy", page_text: str = "") -> None:
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


def convert_transcript_to_text(transcript: "DiarizedTranscript") -> str:
    text_segments: list[str] = []
    for segment in transcript:
        start_time = "{:02d}:{:02d}:{:02d}".format(
            int(segment["start"]) // 3600, int(segment["start"]) // 60 % 60, int(segment["start"]) % 60
        )

        text = f"{start_time}-{segment['speaker']}<br>{segment['text']}"
        text_segments.append(text)

    return "\n\n".join(text_segments)


def convert_to_wiki(episode_data: "EpisodeData", segments: "Segments", episode_image: str) -> str:
    components = [
        f"Episode #{episode_data.podcast.episode_number}",
        f"Title: {episode_data.podcast.official_title}",
        f"Download URL: {episode_data.podcast.download_url}",
        f"Link: {episode_data.podcast.link}",
        f"Episode Image (link): {episode_image}",
        ("Segments:\n\n" + "\n\n".join(str(s) for s in segments)),
        f"Transcript:\n\n{convert_transcript_to_text(episode_data.transcript)}",
    ]

    return "\n\n\n\n".join(components)
