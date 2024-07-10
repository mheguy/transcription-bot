from http.client import NOT_FOUND
from typing import TYPE_CHECKING

from sgu.config import WIKI_EPISODE_URL_BASE

if TYPE_CHECKING:
    from requests import Session


def has_wiki_page(client: "Session", episode_number: int) -> bool:
    resp = client.get(WIKI_EPISODE_URL_BASE + str(episode_number))

    if resp.status_code == NOT_FOUND:
        return False

    resp.raise_for_status()

    return True
