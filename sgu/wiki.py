import os
from http.client import NOT_FOUND
from typing import TYPE_CHECKING

from requests import RequestException

from sgu.config import WIKI_API_BASE, WIKI_EPISODE_URL_BASE
from sgu.data_gathering import gather_data
from sgu.episode_segments import BaseSegment, QuoteSegment
from sgu.parsers.episode_data import convert_episode_data_to_episode_segments
from sgu.parsers.show_notes import get_episode_image_url
from sgu.template_environment import template_env

if TYPE_CHECKING:
    from requests import Session

    from sgu.data_gathering import EpisodeData
    from sgu.parsers.rss_feed import PodcastEpisode
    from sgu.transcription import DiarizedTranscript


# region public functions


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

    episode_icon_name = _find_image_upload(client, str(episode_data.podcast.episode_number))

    if not episode_icon_name:
        episode_image_url = get_episode_image_url(episode_data.show_notes)
        episode_icon_name = _upload_image_to_wiki(client, episode_image_url, episode_data.podcast.episode_number)

    print("Merging data...")
    episode_segments = convert_episode_data_to_episode_segments(episode_data)
    qotw_segment = _extract_quote_of_the_week_for_wiki(episode_segments)

    # TODO: Split transcript by episode segment
    wiki_segments = "\n".join(s.to_wiki() for s in episode_segments)  # convert segments to wiki
    pretty_transcript = _get_pretty_transcript(episode_data.transcript)

    print("Creating wiki page...")
    wiki_page = _construct_wiki_page(episode_data, episode_icon_name, wiki_segments, pretty_transcript, qotw_segment)
    _edit_page(client, page_text=wiki_page)  # TODO: Change for "Create page"


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


def log_into_wiki(client: "Session") -> str:
    """Perform a login to the wiki and return the csrf token."""
    login_token = _get_login_token(client)
    _send_credentials(client, login_token)

    return _get_csrf_token(client)


# endregion
# region private functions


def _find_image_upload(client: "Session", episode_number: str) -> str:
    params = {"action": "query", "list": "allimages", "aiprefix": episode_number, "format": "json"}
    response = client.get(WIKI_API_BASE, params=params)
    data = response.json()

    files = data.get("query", {}).get("allimages", [])
    return files[0]["name"] if files else ""


def _upload_image_to_wiki(client: "Session", image_url: str, episode_number: int) -> str:
    image_response = client.get(image_url)
    image_data = image_response.content

    filename = f"{episode_number}.{image_url.split('.')[-1]}"

    csrf_token = log_into_wiki(client)
    upload_params = {
        "action": "upload",
        "filename": filename,
        "format": "json",
        "token": csrf_token,
    }
    files = {"file": (filename, image_data)}

    upload_response = client.post(WIKI_API_BASE, data=upload_params, files=files)
    upload_response.raise_for_status()

    upload_data = upload_response.json()
    if "error" in upload_data:
        raise RequestException(f"Error uploading image: {upload_data['error']['info']}")

    return filename


def _extract_quote_of_the_week_for_wiki(segments: list["BaseSegment"]) -> QuoteSegment | None:
    for segment in segments:
        if isinstance(segment, QuoteSegment):
            return segment

    return None


def _get_pretty_transcript(transcript: "DiarizedTranscript") -> str:
    for transcript_chunk in transcript:
        if "SPEAKER_" in transcript_chunk["speaker"]:
            name = "US#" + transcript_chunk["speaker"].split("_")[1]
            transcript_chunk["speaker"] = name
        else:
            transcript_chunk["speaker"] = transcript_chunk["speaker"][0]

    text_segments: list[str] = []
    for transcript_chunk in transcript:
        start_time = "{:02d}:{:02d}:{:02d}".format(
            int(transcript_chunk["start"]) // 3600,
            int(transcript_chunk["start"]) // 60 % 60,
            int(transcript_chunk["start"]) % 60,
        )

        text = f"{start_time}<br />\n'''{transcript_chunk['speaker']}''':{transcript_chunk['text']}<br />\n"
        text_segments.append(text)

    return "".join(text_segments)


def _construct_wiki_page(
    episode_data: "EpisodeData",
    episode_icon_name: str,
    segment_text: str,
    transcript: str,
    qotw_segment: QuoteSegment | None,
) -> str:
    template = template_env.get_template("base.j2x")

    num = str(episode_data.podcast.episode_number)
    episode_group_number = num[0] + "0" * (len(num) - 1) + "s"

    if qotw_segment:
        quote_of_the_week = qotw_segment.quote
        quote_of_the_week_attribution = qotw_segment.attribution
    else:
        quote_of_the_week = ""
        quote_of_the_week_attribution = ""

    return template.render(
        segment_text=segment_text,
        transcript=transcript,
        episode_number=episode_data.podcast.episode_number,
        episode_group_number=episode_group_number,
        episode_icon_name=episode_icon_name,
        quote_of_the_week=quote_of_the_week,
        quote_of_the_week_attribution=quote_of_the_week_attribution,
        is_bob_present=episode_data.rogue_attendance.get("bob"),
        is_cara_present=episode_data.rogue_attendance.get("cara"),
        is_jay_present=episode_data.rogue_attendance.get("jay"),
        is_evan_present=episode_data.rogue_attendance.get("evan"),
        is_george_present=episode_data.rogue_attendance.get("george"),
        is_rebecca_present=episode_data.rogue_attendance.get("rebecca"),
        is_perry_present=episode_data.rogue_attendance.get("perry"),
        forum_link="",  # TODO: Add forum link
    )


def _edit_page(client: "Session", page_title: str = "User:Mheguy", page_text: str = "") -> None:
    csrf_token = log_into_wiki(client)

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


# endregion
