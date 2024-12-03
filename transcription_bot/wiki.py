from functools import cache
from http.client import NOT_FOUND
from typing import TYPE_CHECKING

import pywikibot
from mwparserfromhell.utils import parse_anything as parse_wiki
from requests import RequestException

from transcription_bot.config import config
from transcription_bot.data_models import SguListEntry
from transcription_bot.episode_segments import QuoteSegment, Segments
from transcription_bot.global_logger import logger
from transcription_bot.helpers import get_first_segment_of_type
from transcription_bot.llm_interface import ask_llm_for_image_caption
from transcription_bot.parsers.show_notes import get_episode_image_url
from transcription_bot.templating import get_template

if TYPE_CHECKING:
    from collections.abc import Container

    from mwparserfromhell.nodes import Template
    from mwparserfromhell.nodes.extras.parameter import Parameter
    from mwparserfromhell.wikicode import Wikicode
    from requests import Session

    from transcription_bot.data_models import EpisodeData


_EPISODE_PAGE_PREFIX = "SGU_Episode_"
_EPISODE_LIST_PAGE_PREFIX = "Template:EpisodeList"


# region public functions
def create_podcast_wiki_page(
    client: "Session",
    episode_data: "EpisodeData",
    episode_segments: Segments,
    rogues: "Container[str]",
    *,
    allow_page_editing: bool,
) -> None:
    """Creates a wiki page for a podcast episode.

    This function gathers all the necessary data for the episode, merges the data into segments,
    and converts the segments into wiki page content.
    """
    wiki_segment_text = "\n".join(s.to_wiki() for s in episode_segments)
    qotw_segment = get_first_segment_of_type(episode_segments, QuoteSegment)

    episode_image_url = get_episode_image_url(episode_data.show_notes)
    episode_icon_caption = ask_llm_for_image_caption(episode_data.podcast, episode_image_url)

    csrf_token = log_into_wiki(client)

    # Image upload
    episode_icon_name = _find_image_upload(client, str(episode_data.podcast.episode_number))
    if not episode_icon_name:
        logger.debug("Uploading image for episode...")
        episode_icon_name = _upload_image_to_wiki(
            client, csrf_token, episode_image_url, episode_data.podcast.episode_number
        )

    logger.debug("Creating wiki page...")
    wiki_page = _construct_wiki_page(
        episode_data, episode_icon_name, episode_icon_caption, wiki_segment_text, qotw_segment, rogues
    )

    page_title = f"{_EPISODE_PAGE_PREFIX}{episode_data.podcast.episode_number}"

    save_wiki_page(client, page_title, wiki_page, allow_page_editing=allow_page_editing)


def episode_has_wiki_page(client: "Session", episode_number: int) -> bool:
    """Check if an episode has a wiki page.

    Args:
        client (Session): The HTTP client session.
        episode_number (int): The episode number.

    Returns:
        bool: True if the episode has a wiki page, False otherwise.
    """
    resp = client.get(config.wiki_episode_url_base + str(episode_number))

    if resp.status_code == NOT_FOUND:
        return False

    resp.raise_for_status()

    return True


@cache
def log_into_wiki(client: "Session") -> str:
    """Perform a login to the wiki and return the csrf token."""
    login_token = _get_login_token(client)
    _send_credentials(client, login_token)

    return _get_csrf_token(client)


def save_wiki_page(
    client: "Session",
    page_title: str,
    page_text: str,
    *,
    allow_page_editing: bool,
) -> None:
    """Create a wiki page."""
    csrf_token = log_into_wiki(client)

    payload = {
        "action": "edit",
        "title": page_title,
        "summary": "Page created (or rewritten) by transcription-bot. https://github.com/mheguy/transcription-bot",
        "format": "json",
        "text": page_text,
        "notminor": True,
        "bot": True,
        "token": csrf_token,
        "createonly": True,
    }

    if allow_page_editing:
        payload.pop("createonly")

    resp = client.post(config.wiki_api_base, data=payload)
    resp.raise_for_status()
    data = resp.json()

    if "error" in data:
        raise RequestException("Error during page creation: %s", data["error"])

    logger.debug(data)


def update_episode_list(client: "Session", year: int, page_text: str) -> None:
    """Update an episode list."""
    save_wiki_page(client, f"{_EPISODE_LIST_PAGE_PREFIX}{year}", page_text, allow_page_editing=True)


def get_episode_wiki_page(episode_number: int) -> "Wikicode":
    """Retrieve the wiki page with the episode number."""
    return get_wiki_page(f"{_EPISODE_PAGE_PREFIX}{episode_number}")


def get_episode_list_wiki_page(year: int) -> "Wikicode":
    """Retrieve the wiki page with the episode number."""
    return get_wiki_page(f"{_EPISODE_LIST_PAGE_PREFIX}{year}")


def get_episode_entry_from_list(episode_list_page: "Wikicode", episode_number: str) -> SguListEntry | None:
    """Convert a wiki page to an SguListEntry."""
    template = get_episode_template_from_list(episode_list_page, episode_number)
    if template is None:
        return None

    return SguListEntry.from_template(template)


def get_episode_template_from_list(episode_list_page: "Wikicode", episode_number: str) -> "Template | None":
    """Return the raw tuple from a wiki episode list."""
    templates: list[Template] = episode_list_page.filter_templates()
    for template in templates:
        if template.name.matches(SguListEntry.identifier) and template.has("episode"):
            param: Parameter = template.get("episode")

            if param.value.strip_code() == str(episode_number):
                return template

    return None


@cache
def get_wiki_page(page_title: str) -> "Wikicode":
    """Retrieve the wiki page with the given name."""
    logger.debug(f"Retrieving wiki page: {page_title}")
    site = pywikibot.Site(url=config.wiki_base_url)
    page = pywikibot.Page(site, page_title).text
    return parse_wiki(page)


# endregion
# region private functions
def _find_image_upload(client: "Session", episode_number: str) -> str:
    params = {"action": "query", "list": "allimages", "aiprefix": episode_number, "format": "json"}
    response = client.get(config.wiki_api_base, params=params)
    data = response.json()

    files = data.get("query", {}).get("allimages", [])
    return files[0]["name"] if files else ""


def _upload_image_to_wiki(client: "Session", csrf_token: str, image_url: str, episode_number: int) -> str:
    image_response = client.get(image_url)
    image_data = image_response.content

    filename = f"{episode_number}.{image_url.split('.')[-1]}"

    upload_params = {
        "action": "upload",
        "filename": filename,
        "format": "json",
        "token": csrf_token,
    }
    files = {"file": (filename, image_data)}

    upload_response = client.post(config.wiki_api_base, data=upload_params, files=files)
    upload_response.raise_for_status()

    upload_data = upload_response.json()
    if "error" in upload_data:
        raise RequestException(f"Error uploading image: {upload_data['error']['info']}")

    return filename


def _construct_wiki_page(
    episode_data: "EpisodeData",
    episode_icon_name: str,
    episode_icon_caption: str,
    segment_text: str,
    qotw_segment: QuoteSegment | None,
    rogues: "Container[str]",
) -> str:
    template = get_template("base")

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
        is_bob_present=("bob" in rogues and "y") or "",
        is_cara_present=("cara" in rogues and "y") or "",
        is_jay_present=("jay" in rogues and "y") or "",
        is_evan_present=("evan" in rogues and "y") or "",
        is_george_present=("george" in rogues and "y") or "",
        is_rebecca_present=("rebecca" in rogues and "y") or "",
        is_perry_present=("perry" in rogues and "y") or "",
        forum_link="",
    )


def _get_login_token(client: "Session") -> str:
    params = {"action": "query", "meta": "tokens", "type": "login", "format": "json"}

    resp = client.get(url=config.wiki_api_base, params=params)
    resp.raise_for_status()
    data = resp.json()

    return data["query"]["tokens"]["logintoken"]


def _send_credentials(client: "Session", login_token: str) -> None:
    payload = {
        "action": "login",
        "lgname": config.wiki_username,
        "lgpassword": config.wiki_password,
        "lgtoken": login_token,
        "format": "json",
    }

    resp = client.post(config.wiki_api_base, data=payload)
    resp.raise_for_status()

    if resp.json()["login"]["result"] != "Success":
        raise ValueError(f"Login failed: {resp.json()}")


def _get_csrf_token(client: "Session") -> str:
    params = {"action": "query", "meta": "tokens", "format": "json"}

    resp = client.get(url=config.wiki_api_base, params=params)
    resp.raise_for_status()
    data = resp.json()

    return data["query"]["tokens"]["csrftoken"]


# endregion
