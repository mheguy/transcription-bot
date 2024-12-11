from http.client import NOT_FOUND
from unittest.mock import MagicMock, create_autospec, patch

import pytest

from transcription_bot.interfaces import wiki
from transcription_bot.utils.global_http_client import HttpClient

# Test constants
TEST_EPISODE_NUMBER = "123"
TEST_LOGIN_TOKEN = "test_login_token"  # noqa: S105
TEST_CSRF_TOKEN = "test_csrf_token"  # noqa: S105
TEST_QUOTE = "Test quote"
TEST_ATTRIBUTION = "Test attribution"
TEST_WIKI_TEXT = "Quote segment wiki text"
TEST_PAGE_TITLE = "Test Page"
TEST_PAGE_CONTENT = "Test content"
TEST_SHOW_NOTES = "Episode show notes"


@pytest.fixture(name="http_client")
def mock_http_client() -> MagicMock:
    http_client = create_autospec(HttpClient)
    # Set up default successful responses
    http_client.get.return_value.status_code = 200
    http_client.get.return_value.json.return_value = {
        "query": {"tokens": {"logintoken": TEST_LOGIN_TOKEN, "csrftoken": TEST_CSRF_TOKEN}}
    }
    http_client.post.return_value.status_code = 200
    http_client.post.return_value.json.return_value = {"login": {"result": "Success"}}
    return http_client


def test_log_into_wiki(http_client: MagicMock):
    # Act
    csrf_token = wiki.log_into_wiki(http_client)

    # Assert
    assert csrf_token == TEST_CSRF_TOKEN
    assert http_client.get.call_count == 2  # Login token and CSRF token
    assert http_client.post.call_count == 1  # Send credentials


def test_episode_has_wiki_page_exists(http_client: MagicMock):
    # Arrange
    http_client.get.return_value.status_code = 200

    # Act
    result = wiki.episode_has_wiki_page(http_client, 123)

    # Assert
    assert result is True
    http_client.get.assert_called_once()


def test_episode_has_wiki_page_not_exists(http_client: MagicMock):
    # Arrange
    http_client.get.return_value.status_code = NOT_FOUND

    # Act
    result = wiki.episode_has_wiki_page(http_client, 123)

    # Assert
    assert result is False
    http_client.get.assert_called_once()


def test_save_wiki_page(http_client: MagicMock):
    # Arrange
    with patch("transcription_bot.interfaces.wiki.log_into_wiki") as mock_login:
        mock_login.return_value = TEST_CSRF_TOKEN

        # Act
        wiki.save_wiki_page(http_client, TEST_PAGE_TITLE, TEST_PAGE_CONTENT, allow_page_editing=True)

        # Assert
        http_client.post.assert_called_once()
        _, kwargs = http_client.post.call_args
        assert kwargs["data"]["title"] == TEST_PAGE_TITLE
        assert kwargs["data"]["text"] == TEST_PAGE_CONTENT
