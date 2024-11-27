from http.client import NOT_FOUND
from unittest.mock import MagicMock, patch

import pytest
from requests import RequestException, Session

from transcription_bot import wiki
from transcription_bot.data_gathering import EpisodeData
from transcription_bot.episode_segments import QuoteSegment, Segments
from transcription_bot.parsers.rss_feed import PodcastRssEntry

# Test constants
TEST_EPISODE_NUMBER = "123"
TEST_LOGIN_TOKEN = "test_login_token"  # noqa: S105
TEST_CSRF_TOKEN = "test_csrf_token"  # noqa: S105
TEST_IMAGE_URL = "http://example.com/image.jpg"
TEST_IMAGE_FILENAME = "test_image.jpg"
TEST_UPLOADED_IMAGE = "uploaded_image.jpg"
TEST_IMAGE_CAPTION = "Test caption"
TEST_QUOTE = "Test quote"
TEST_ATTRIBUTION = "Test attribution"
TEST_WIKI_TEXT = "Quote segment wiki text"
TEST_PAGE_TITLE = "Test Page"
TEST_PAGE_CONTENT = "Test content"
TEST_SHOW_NOTES = "Episode show notes"


@pytest.fixture()
def mock_session() -> MagicMock:
    session = MagicMock(spec=Session)
    # Set up default successful responses
    session.get.return_value.status_code = 200
    session.get.return_value.json.return_value = {
        "query": {"tokens": {"logintoken": TEST_LOGIN_TOKEN, "csrftoken": TEST_CSRF_TOKEN}}
    }
    session.post.return_value.status_code = 200
    session.post.return_value.json.return_value = {"login": {"result": "Success"}}
    return session


@pytest.fixture()
def mock_episode_data() -> MagicMock:
    episode_data = MagicMock(spec=EpisodeData)
    episode_data.podcast = MagicMock(spec=PodcastRssEntry)
    episode_data.podcast.episode_number = TEST_EPISODE_NUMBER
    episode_data.transcript = [{"speaker": "Bob"}, {"speaker": "Alice"}]
    episode_data.show_notes = TEST_SHOW_NOTES
    return episode_data


@pytest.fixture()
def mock_segments() -> MagicMock:
    quote_segment = MagicMock(spec=QuoteSegment)
    quote_segment.to_wiki.return_value = TEST_WIKI_TEXT
    quote_segment.quote = TEST_QUOTE
    quote_segment.attribution = TEST_ATTRIBUTION
    segments = MagicMock(spec=Segments)
    segments.__iter__.return_value = [quote_segment]
    return segments


def test_log_into_wiki(mock_session: MagicMock):
    # Act
    csrf_token = wiki.log_into_wiki(mock_session)

    # Assert
    assert csrf_token == TEST_CSRF_TOKEN
    assert mock_session.get.call_count == 2  # Login token and CSRF token
    assert mock_session.post.call_count == 1  # Send credentials


def test_log_into_wiki_failed_login(mock_session: MagicMock):
    # Arrange
    mock_session.post.return_value.status_code = 401
    mock_session.post.return_value.raise_for_status.side_effect = RequestException("Login failed")

    # Assert
    with pytest.raises(RequestException):
        # Act
        wiki.log_into_wiki(mock_session)


def test_episode_has_wiki_page_exists(mock_session: MagicMock):
    # Arrange
    mock_session.get.return_value.status_code = 200

    # Act
    result = wiki.episode_has_wiki_page(mock_session, 123)

    # Assert
    assert result is True
    mock_session.get.assert_called_once()


def test_episode_has_wiki_page_not_exists(mock_session: MagicMock):
    # Arrange
    mock_session.get.return_value.status_code = NOT_FOUND

    # Act
    result = wiki.episode_has_wiki_page(mock_session, 123)

    # Assert
    assert result is False
    mock_session.get.assert_called_once()


def test_episode_has_wiki_page_error(mock_session: MagicMock):
    # Arrange
    mock_session.get.return_value.status_code = 500
    mock_session.get.return_value.raise_for_status.side_effect = RequestException("Server error")

    # Act/Assert
    with pytest.raises(RequestException):
        wiki.episode_has_wiki_page(mock_session, 123)


def test_save_wiki_page(mock_session: MagicMock):
    # Arrange
    with patch("transcription_bot.wiki.log_into_wiki") as mock_login:
        mock_login.return_value = TEST_CSRF_TOKEN

        # Act
        wiki.save_wiki_page(mock_session, TEST_PAGE_TITLE, TEST_PAGE_CONTENT, allow_page_editing=True)

        # Assert
        mock_session.post.assert_called_once()
        _, kwargs = mock_session.post.call_args
        assert kwargs["data"]["title"] == TEST_PAGE_TITLE
        assert kwargs["data"]["text"] == TEST_PAGE_CONTENT


def test_create_podcast_wiki_page(mock_session: MagicMock, mock_episode_data: MagicMock, mock_segments: MagicMock):
    # Arrange
    with patch.multiple(
        "transcription_bot.wiki",
        log_into_wiki=MagicMock(return_value=TEST_CSRF_TOKEN),
        _find_image_upload=MagicMock(return_value=TEST_IMAGE_FILENAME),
        _upload_image_to_wiki=MagicMock(return_value=TEST_UPLOADED_IMAGE),
        get_episode_image_url=MagicMock(return_value=TEST_IMAGE_URL),
        ask_llm_for_image_caption=MagicMock(return_value=TEST_IMAGE_CAPTION),
    ):
        # Act
        wiki.create_podcast_wiki_page(mock_session, mock_episode_data, mock_segments, allow_page_editing=True)

        # Assert
        mock_session.post.assert_called()
        _, kwargs = mock_session.post.call_args
        assert f"SGU_Episode_{TEST_EPISODE_NUMBER}" in str(kwargs)


def test_create_podcast_wiki_page_failed_image_upload(
    mock_session: MagicMock, mock_episode_data: MagicMock, mock_segments: MagicMock
):
    # Arrange
    with (
        patch.multiple(
            "transcription_bot.wiki",
            log_into_wiki=MagicMock(return_value=TEST_CSRF_TOKEN),
            _find_image_upload=MagicMock(return_value=None),
            _upload_image_to_wiki=MagicMock(side_effect=RequestException("Upload failed")),
            get_episode_image_url=MagicMock(return_value=TEST_IMAGE_URL),
            ask_llm_for_image_caption=MagicMock(return_value=TEST_IMAGE_CAPTION),
        ),
        # Assert
        pytest.raises(RequestException),
    ):
        # Act
        wiki.create_podcast_wiki_page(mock_session, mock_episode_data, mock_segments, allow_page_editing=True)
