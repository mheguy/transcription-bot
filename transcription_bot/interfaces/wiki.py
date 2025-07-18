import logging
from dataclasses import dataclass
from functools import cache
from http.client import NOT_FOUND

from loguru import logger
from mwparserfromhell.nodes.template import Template
from mwparserfromhell.utils import parse_anything as parse_wiki
from mwparserfromhell.wikicode import Wikicode
from requests import RequestException
from tenacity import RetryCallState, before_sleep_log, retry, stop_after_attempt, wait_fixed

from transcription_bot.models.data_models import SguListEntry
from transcription_bot.utils.config import config
from transcription_bot.utils.global_http_client import HttpClient, http_client

EPISODE_PAGE_PREFIX = "SGU_Episode_"
EPISODE_LIST_PAGE_PREFIX = "Template:EpisodeList"
_BASE_ACTION_PARAMS = {"action": "query", "meta": "tokens", "format": "json"}
_LOGIN_ACTION_PARAMS = {"type": "login", **_BASE_ACTION_PARAMS}


# region Module state
@dataclass
class _WikiClient:
    csrf_token: str | None = None
    http_client: HttpClient = http_client


_wiki_client = _WikiClient()


# endregion
# region public functions
@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    reraise=True,
    after=lambda state: _force_login(state),
    before_sleep=before_sleep_log(logging.getLogger(), logging.WARNING),
)
def save_wiki_page(page_title: str, page_text: str, *, allow_page_editing: bool) -> None:
    """Create a wiki page."""
    csrf_token = get_csrf_token()

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

    resp = _wiki_client.http_client.post(config.wiki_api_base, data=payload)
    data = resp.json()

    if "error" in data:
        raise RequestException("Error during page creation: %s", data["error"])

    logger.debug(data)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    reraise=True,
    after=lambda state: _force_login(state),
    before_sleep=before_sleep_log(logging.getLogger(), logging.WARNING),
)
def upload_image_to_wiki(image_url: str, episode_number: int) -> str:
    """Upload an image to the wiki."""
    image_response = _wiki_client.http_client.get(image_url)
    image_data = image_response.content

    filename = f"{episode_number}.{image_url.split('.')[-1]}"

    upload_params = {
        "action": "upload",
        "filename": filename,
        "format": "json",
        "token": get_csrf_token(),
    }
    files = {"file": (filename, image_data)}

    upload_response = _wiki_client.http_client.post(config.wiki_api_base, data=upload_params, files=files)

    upload_data = upload_response.json()
    if "error" in upload_data:
        raise RequestException(f"Error uploading image: {upload_data['error']['info']}")

    return filename


def episode_has_wiki_page(episode_number: int) -> bool:
    """Check if an episode has a wiki page."""
    resp = _wiki_client.http_client.get(config.wiki_episode_url_base + str(episode_number), raise_for_status=False)

    if resp.status_code == NOT_FOUND:
        return False

    resp.raise_for_status()

    return True


def get_episode_wiki_page(episode_number: int) -> Wikicode:
    """Retrieve the wiki page with the episode number."""
    return get_wiki_page(f"{EPISODE_PAGE_PREFIX}{episode_number}")


def get_episode_list_wiki_page(year: int) -> Wikicode:
    """Retrieve the wiki page with the episode number."""
    episode_list = get_wiki_page(f"{EPISODE_LIST_PAGE_PREFIX}{year}")
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
            param = template.get("episode")

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

    req = _wiki_client.http_client.get(config.wiki_api_base, headers=headers, params=params)
    json = req.json()

    if json["query"]["pages"][0].get("missing"):
        raise ValueError(f"Page does not exist in wiki: {page_title}")

    revision = json["query"]["pages"][0]["revisions"][0]
    text = revision["slots"]["main"]["content"]

    return parse_wiki(text)


def find_image_upload(episode_number: str) -> str:
    """Find an image uploaded to the wiki."""
    params = {"action": "query", "list": "allimages", "aiprefix": episode_number, "format": "json"}
    response = _wiki_client.http_client.get(config.wiki_api_base, params=params)
    data = response.json()

    files = data.get("query", {}).get("allimages", [])
    return files[0]["name"] if files else ""


def get_csrf_token() -> str:
    """Perform a login to the wiki and return the csrf token."""
    if _wiki_client.csrf_token:
        return _wiki_client.csrf_token

    login_token = _get_login_token()
    _send_credentials(login_token)

    csrf_token = _get_csrf_token()
    _wiki_client.csrf_token = csrf_token
    return csrf_token


# endregion
# region private functions
def _get_login_token() -> str:
    params = _LOGIN_ACTION_PARAMS

    resp = _wiki_client.http_client.get(url=config.wiki_api_base, params=params)
    data = resp.json()

    return data["query"]["tokens"]["logintoken"]


def _send_credentials(login_token: str) -> None:
    payload = {
        "action": "login",
        "lgname": config.wiki_username,
        "lgpassword": config.wiki_password,
        "lgtoken": login_token,
        "format": "json",
    }

    resp = _wiki_client.http_client.post(config.wiki_api_base, data=payload)

    if resp.json()["login"]["result"] != "Success":
        raise ValueError(f"Login failed: {resp.json()}")


def _get_csrf_token() -> str:
    params = _BASE_ACTION_PARAMS

    resp = _wiki_client.http_client.get(url=config.wiki_api_base, params=params)
    data = resp.json()

    return data["query"]["tokens"]["csrftoken"]


def _force_login(_: RetryCallState) -> None:
    logger.info("Clearing csrf token due to failed login...")
    _wiki_client.csrf_token = None


# endregion
