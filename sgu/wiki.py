import os
from http.client import NOT_FOUND
from typing import TYPE_CHECKING

from requests import RequestException

from sgu.config import WIKI_API_BASE, WIKI_EPISODE_URL_BASE
from sgu.episode_segments import BaseSegment, QuoteSegment, Segments
from sgu.global_logger import logger
from sgu.llm_interface import ask_llm_for_image_caption
from sgu.parsers.show_notes import get_episode_image_url
from sgu.template_environment import template_env

if TYPE_CHECKING:
    from requests import Session

    from sgu.data_gathering import EpisodeData


# region public functions
async def create_podcast_wiki_page(client: "Session", episode_data: "EpisodeData", episode_segments: Segments) -> None:
    """Creates a wiki page for a podcast episode.

    This function gathers all the necessary data for the episode, merges the data into segments,
    and converts the segments into wiki page content.
    """
    # we must grab speaker data before we convert transcript to wiki
    speakers = {s["speaker"].lower() for s in episode_data.transcript}
    wiki_segments = "\n".join(s.to_wiki() for s in episode_segments)
    qotw_segment = _extract_quote_of_the_week_for_wiki(episode_segments)

    episode_image_url = get_episode_image_url(episode_data.show_notes)
    episode_icon_caption = ask_llm_for_image_caption(episode_image_url)

    # Image upload
    episode_icon_name = _find_image_upload(client, str(episode_data.podcast.episode_number))
    if not episode_icon_name:
        logger.debug("Uploading image for episode...")
        episode_icon_name = _upload_image_to_wiki(client, episode_image_url, episode_data.podcast.episode_number)

    logger.debug("Creating wiki page...")
    wiki_page = _construct_wiki_page(
        episode_data, episode_icon_name, episode_icon_caption, wiki_segments, qotw_segment, speakers
    )

    page_title = f"SGU_Episode_{episode_data.podcast.episode_number}"

    _create_page(client, page_title, wiki_page)


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


def _construct_wiki_page(
    episode_data: "EpisodeData",
    episode_icon_name: str,
    episode_icon_caption: str,
    segment_text: str,
    qotw_segment: QuoteSegment | None,
    speakers: set[str],
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
        episode_number=episode_data.podcast.episode_number,
        episode_group_number=episode_group_number,
        episode_icon_name=episode_icon_name,
        episode_icon_caption=episode_icon_caption,
        quote_of_the_week=quote_of_the_week,
        quote_of_the_week_attribution=quote_of_the_week_attribution,
        is_bob_present="bob" in speakers and "y" or "",
        is_cara_present="cara" in speakers and "y" or "",
        is_jay_present="jay" in speakers and "y" or "",
        is_evan_present="evan" in speakers and "y" or "",
        is_george_present="george" in speakers and "y" or "",
        is_rebecca_present="rebecca" in speakers and "y" or "",
        is_perry_present="perry" in speakers and "y" or "",
        forum_link="",
    )


def _create_page(client: "Session", page_title: str, page_text: str) -> None:
    csrf_token = log_into_wiki(client)

    payload = {
        "action": "edit",
        "title": page_title,
        "format": "json",
        "text": page_text,
        "notminor": True,
        "bot": True,
        "token": csrf_token,
        "createonly": True,
    }

    resp = client.post(WIKI_API_BASE, data=payload)
    resp.raise_for_status()
    data = resp.json()

    logger.debug(data)


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
