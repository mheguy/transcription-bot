# pyright: reportPrivateUsage=false
from http.client import NOT_FOUND
from unittest.mock import MagicMock, Mock, create_autospec, patch

import pytest
from tenacity import wait_fixed

from transcription_bot.interfaces import wiki
from transcription_bot.utils.global_http_client import HttpClient

# Test constants
TEST_LOGIN_TOKEN = "test_login_token"  # noqa: S105
TEST_CSRF_TOKEN = "test_csrf_token"  # noqa: S105
TEST_PAGE_CONTENT = "Test content"


@pytest.fixture(autouse=True)
def reset_module_state() -> None:
    wiki._wiki_client = wiki._WikiClient()


def create_token_response(key: str, value: str) -> dict[str, dict[str, dict[str, str]]]:
    return {"query": {"tokens": {key: value}}}


@pytest.fixture(name="http_client")
def mock_http_client(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    http_client = create_autospec(HttpClient)
    # Set up default successful responses
    http_client.get.return_value.status_code = 200
    http_client.get.return_value.json.return_value = {
        "query": {"tokens": {"logintoken": TEST_LOGIN_TOKEN, "csrftoken": TEST_CSRF_TOKEN}}
    }
    http_client.post.return_value.status_code = 200
    http_client.post.return_value.json.return_value = {"login": {"result": "Success"}}

    monkeypatch.setattr(wiki._wiki_client, "http_client", http_client)
    return http_client


def test_get_csrf_token(http_client: MagicMock):
    # Act
    csrf_token = wiki.get_csrf_token()

    # Assert
    assert csrf_token == TEST_CSRF_TOKEN
    assert http_client.get.call_count == 2  # Login token and CSRF token
    assert http_client.post.call_count == 1  # Send credentials
    assert wiki._wiki_client.csrf_token == TEST_CSRF_TOKEN


def test_get_csrf_token_with_cached_token(http_client: MagicMock, monkeypatch: pytest.MonkeyPatch):
    # Arrange
    token = "test_get_csrf_token_with_cached_token"  # noqa: S105
    monkeypatch.setattr(wiki._wiki_client, "csrf_token", token)

    # Act
    csrf_token = wiki.get_csrf_token()

    # Assert
    assert csrf_token == token
    http_client.assert_not_called()


def test_episode_has_wiki_page_exists(http_client: MagicMock):
    # Arrange
    http_client.get.return_value.status_code = 200

    # Act
    result = wiki.episode_has_wiki_page(123)

    # Assert
    assert result is True
    http_client.get.assert_called_once()


def test_episode_has_wiki_page_not_exists(http_client: MagicMock):
    # Arrange
    http_client.get.return_value.status_code = NOT_FOUND

    # Act
    result = wiki.episode_has_wiki_page(123)

    # Assert
    assert result is False
    http_client.get.assert_called_once()


def test_save_wiki_page(http_client: MagicMock):
    # Arrange
    page_title = "bloop"

    with patch("transcription_bot.interfaces.wiki.get_csrf_token") as mock_get_csrf_token:
        mock_get_csrf_token.return_value = TEST_CSRF_TOKEN

        # Act
        wiki.save_wiki_page(page_title, TEST_PAGE_CONTENT, allow_page_editing=True)

        # Assert
        http_client.post.assert_called_once()
        _, kwargs = http_client.post.call_args
        assert kwargs["data"]["text"] == TEST_PAGE_CONTENT


def test_save_wiki_page_retries_on_error(http_client: MagicMock, monkeypatch: pytest.MonkeyPatch):
    # Arrange
    # Speed up retry logic and disable logging
    monkeypatch.setattr(wiki.save_wiki_page.retry, "wait", wait_fixed(0))  # type: ignore
    monkeypatch.setattr(wiki.save_wiki_page.retry, "before_sleep", lambda _: None)  # type: ignore
    page_title = "bloop"

    with patch("transcription_bot.interfaces.wiki.get_csrf_token") as mock_get_csrf_token:
        mock_get_csrf_token.side_effect = [Exception("expected error"), TEST_CSRF_TOKEN]

        # Act
        wiki.save_wiki_page(page_title, TEST_PAGE_CONTENT, allow_page_editing=True)

        # Assert
        http_client.post.assert_called_once()
        _, kwargs = http_client.post.call_args
        assert kwargs["data"]["text"] == TEST_PAGE_CONTENT


def test_save_wiki_page_obtains_new_csrf_token_on_error(http_client: MagicMock, monkeypatch: pytest.MonkeyPatch):
    # Arrange
    page_title = "bloop"

    token = "bad_token"  # noqa: S105
    monkeypatch.setattr(wiki._wiki_client, "csrf_token", token)

    # Speed up retry logic and disable logging
    monkeypatch.setattr(wiki.save_wiki_page.retry, "wait", wait_fixed(0))  # type: ignore
    monkeypatch.setattr(wiki.save_wiki_page.retry, "before_sleep", lambda _: None)  # type: ignore

    http_client.post.side_effect = [
        Exception("expected error"),
        Mock(json=Mock(return_value={"login": {"result": "Success"}})),
        Mock(json=Mock(return_value={})),
    ]

    # Act
    wiki.save_wiki_page(page_title, TEST_PAGE_CONTENT, allow_page_editing=True)

    # Assert
    assert http_client.post.call_count == 3
    _, kwargs = http_client.post.call_args
    assert kwargs["data"]["token"] == TEST_CSRF_TOKEN
