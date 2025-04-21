from transcription_bot.models.episode_segments import science_or_fiction

# Constants for test data
_TEST_ARTICLE_URL = "http://example.com"
_TEST_ARTICLE_TITLE = "Test Article"
_TEST_ARTICLE_PUBLICATION = "Test Publication"
_TEST_ITEM_TEXT = "Test item"


def test_science_or_fiction_item():
    # Arrange
    item = science_or_fiction.ScienceOrFictionItem(
        number=1,
        name=_TEST_ITEM_TEXT,
        article_url=_TEST_ARTICLE_URL,
        sof_result="correct",
        article_title=_TEST_ARTICLE_TITLE,
        article_publication=_TEST_ARTICLE_PUBLICATION,
    )

    # Assert
    assert item.number == 1
    assert item.name == _TEST_ITEM_TEXT
    assert item.article_url == _TEST_ARTICLE_URL
