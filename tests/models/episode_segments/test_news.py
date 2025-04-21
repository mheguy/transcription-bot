from transcription_bot.models.episode_segments import news

# Constants for test data
_TEST_ARTICLE_URL = "http://example.com"
_TEST_TOPIC = "Test Topic"


def test_news_item():
    # Arrange
    item = news.NewsItem(item_number=1, topic=_TEST_TOPIC, url=_TEST_ARTICLE_URL)

    # Assert
    assert item.item_number == 1
    assert item.topic == _TEST_TOPIC
    assert item.url == _TEST_ARTICLE_URL


def test_news_meta_segment():
    # Arrange
    news_topic = "News 1"

    news_items = [
        news.NewsItem(item_number=1, topic=news_topic, url=f"{_TEST_ARTICLE_URL}1"),
        news.NewsItem(item_number=2, topic="News 2", url=f"{_TEST_ARTICLE_URL}2"),
    ]

    # Act
    segment = news.NewsMetaSegment(news_segments=news_items)

    # Assert
    assert len(segment.news_segments) == 2
    assert segment.news_segments[0].topic == news_topic
