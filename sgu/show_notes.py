import pickle
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup, Comment, Tag

from sgu.config import END_HEADER_COMMENT, END_POST_COMMENT, START_HEADER_COMMENT, START_POST_COMMENT

if TYPE_CHECKING:
    from requests import Session


def get_show_notes(client: "Session", url: str) -> BeautifulSoup:
    resp = client.get(url)
    resp.raise_for_status()

    return BeautifulSoup(resp.content, "html.parser")


def extract_content_between_two_comments(soup: BeautifulSoup, top_comment: str, bottom_comment: str) -> Tag:
    start_comment = soup.find(string=lambda text: isinstance(text, Comment) and top_comment in text)
    end_comment = soup.find(string=lambda text: isinstance(text, Comment) and bottom_comment in text)

    if not start_comment or not end_comment:
        raise ValueError("Could not find start or end comment")

    content: list[Tag] = []
    for sibling in start_comment.next_siblings:
        if sibling == end_comment:
            break
        if isinstance(sibling, Tag):
            content.append(sibling)

    if len(content) != 1:
        raise ValueError("Unexpected number of content elements extracted")

    return content[0]


def process_header(header_element: Tag) -> None: ...


def process_post(post_element: Tag) -> None: ...


html: bytes = pickle.load(open("show_notes.pkl", "rb")).content  # noqa: S301, SIM115
soup = BeautifulSoup(html, "html.parser")

header_element = extract_content_between_two_comments(soup, START_HEADER_COMMENT, END_HEADER_COMMENT)
post_element = extract_content_between_two_comments(soup, START_POST_COMMENT, END_POST_COMMENT)

process_header(header_element)
process_post(post_element)
