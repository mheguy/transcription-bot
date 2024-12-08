from functools import cache
from http.client import NOT_FOUND

from mwparserfromhell.nodes import Template
from mwparserfromhell.nodes.extras.parameter import Parameter
from mwparserfromhell.utils import parse_anything as parse_wiki
from mwparserfromhell.wikicode import Wikicode
from requests import RequestException, Session

from transcription_bot.models.data_models import SguListEntry
from transcription_bot.utils.config import config
from transcription_bot.utils.global_http_client import http_client
from transcription_bot.utils.global_logger import logger

_EPISODE_PAGE_PREFIX = "SGU_Episode_"
_EPISODE_LIST_PAGE_PREFIX = "Template:EpisodeList"


# region public functions
def episode_has_wiki_page(client: Session, episode_number: int) -> bool:
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
def log_into_wiki(client: Session) -> str:
    """Perform a login to the wiki and return the csrf token."""
    login_token = _get_login_token(client)
    _send_credentials(client, login_token)

    return _get_csrf_token(client)


def save_wiki_page(
    client: Session,
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


def create_or_update_podcast_page(
    client: Session,
    episode_number: int,
    wiki_page: str,
    *,
    allow_page_editing: bool,
) -> None:
    """Create or update a podcast page."""
    save_wiki_page(client, f"{_EPISODE_PAGE_PREFIX}{episode_number}", wiki_page, allow_page_editing=allow_page_editing)


def update_episode_list(client: Session, year: int, page_text: str) -> None:
    """Update an episode list."""
    save_wiki_page(client, f"{_EPISODE_LIST_PAGE_PREFIX}{year}", page_text, allow_page_editing=True)


def get_episode_wiki_page(episode_number: int) -> Wikicode:
    """Retrieve the wiki page with the episode number."""
    return get_wiki_page(f"{_EPISODE_PAGE_PREFIX}{episode_number}")


def get_episode_list_wiki_page(year: int) -> Wikicode:
    """Retrieve the wiki page with the episode number."""
    episode_list = get_wiki_page(f"{_EPISODE_LIST_PAGE_PREFIX}{year}")
    if not episode_list:
        raise ValueError(f"Could not find episode list for year {year}")

    return episode_list


def get_episode_entry_from_list(episode_list_page: Wikicode, episode_number: str) -> SguListEntry | None:
    """Convert a wiki page to an SguListEntry."""
    template = get_episode_template_from_list(episode_list_page, episode_number)
    if template is None:
        return None

    return SguListEntry.from_template(template)


def get_episode_template_from_list(episode_list_page: Wikicode, episode_number: str) -> Template | None:
    """Return the raw tuple from a wiki episode list."""
    templates: list[Template] = episode_list_page.filter_templates()
    for template in templates:
        if template.name.matches(SguListEntry.identifier) and template.has("episode"):
            param: Parameter = template.get("episode")

            if param.value.strip_code().strip() == str(episode_number):
                return template

    return None


@cache
def get_wiki_page(page_title: str) -> Wikicode:
    """Retrieve the wiki page with the given name."""
    logger.debug(f"Retrieving wiki page: {page_title}")

    params = {
        "action": "query",
        "format": "json",
        "prop": "revisions",
        "titles": page_title,
        "rvprop": "content",
        "rvslots": "main",
        "rvlimit": 1,
        "formatversion": "2",
    }
    headers = {"User-Agent": "transcription-bot/1.0"}

    req = http_client.get(config.wiki_api_base, headers=headers, params=params, timeout=5)
    json = req.json()

    revision = json["query"]["pages"][0]["revisions"][0]
    text = revision["slots"]["main"]["content"]

    return parse_wiki(text)


def find_image_upload(client: Session, episode_number: str) -> str:
    """Find an image uploaded to the wiki."""
    params = {"action": "query", "list": "allimages", "aiprefix": episode_number, "format": "json"}
    response = client.get(config.wiki_api_base, params=params)
    data = response.json()

    files = data.get("query", {}).get("allimages", [])
    return files[0]["name"] if files else ""


def upload_image_to_wiki(client: Session, image_url: str, episode_number: int) -> str:
    """Upload an image to the wiki."""
    csrf_token = log_into_wiki(client)
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


# endregion
# region private functions
def _get_login_token(client: Session) -> str:
    params = {"action": "query", "meta": "tokens", "type": "login", "format": "json"}

    resp = client.get(url=config.wiki_api_base, params=params)
    resp.raise_for_status()
    data = resp.json()

    return data["query"]["tokens"]["logintoken"]


def _send_credentials(client: Session, login_token: str) -> None:
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


def _get_csrf_token(client: Session) -> str:
    params = {"action": "query", "meta": "tokens", "format": "json"}

    resp = client.get(url=config.wiki_api_base, params=params)
    resp.raise_for_status()
    data = resp.json()

    return data["query"]["tokens"]["csrftoken"]


# endregion
