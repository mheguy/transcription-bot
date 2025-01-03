from transcription_bot.models import episode_segments
from transcription_bot.models.simple_models import DiarizedTranscript

# Constants for test data
TEST_ARTICLE_URL = "http://example.com"
TEST_ARTICLE_TITLE = "Test Article"
TEST_ARTICLE_PUBLICATION = "Test Publication"
TEST_ITEM_TEXT = "Test item"
TEST_TOPIC = "Test Topic"
TEST_QUOTE = "Test quote"
TEST_ATTRIBUTION = "John Doe"


def test_format_time():
    assert episode_segments.format_time(None) == "???"
    assert episode_segments.format_time(0.1) == "00:00"
    assert episode_segments.format_time(61.0) == "01:01"
    assert episode_segments.format_time(3661.0) == "1:01:01"


def test_format_transcript_for_wiki():
    # Arrange
    diarized_transcript: DiarizedTranscript = [
        {"speaker": "Steve", "text": "Hello everyone", "start": 0.0, "end": 2.0},
        {"speaker": "Bob", "text": "Welcome to the show", "start": 2.0, "end": 4.0},
    ]

    # Act
    formatted = episode_segments.format_transcript_for_wiki(diarized_transcript)

    # Assert
    assert "'''S:''' Hello everyone" in formatted
    assert "'''B:''' Welcome to the show" in formatted


def test_unknown_segment():
    # Arrange
    test_title = "Test Title"
    test_extra = "Extra Info"

    # Act
    segment = episode_segments.UnknownSegment.create(f"{test_title}\n{test_extra}\n{TEST_ARTICLE_URL}")

    # Assert
    assert segment.title == test_title
    assert segment.extra_text == test_extra
    assert segment.url == TEST_ARTICLE_URL


def test_intro_segment():
    # Arrange
    diarized_transcript: DiarizedTranscript = [
        {"speaker": "Steve", "text": "Hello everyone", "start": 0.0, "end": 2.0},
        {"speaker": "Bob", "text": "Welcome to the show", "start": 2.0, "end": 4.0},
    ]

    segment = episode_segments.IntroSegment()
    segment.transcript = diarized_transcript
    segment.start_time = segment.get_start_time(diarized_transcript)
    segment.end_time = segment.transcript[-1]["end"]

    # Act
    result = segment.get_start_time(diarized_transcript)

    # Assert
    assert result == 0.0
    assert segment.duration > 0


def test_science_or_fiction_item():
    # Arrange
    item = episode_segments.ScienceOrFictionItem(
        number=1,
        name=TEST_ITEM_TEXT,
        article_url=TEST_ARTICLE_URL,
        sof_result="correct",
        article_title=TEST_ARTICLE_TITLE,
        article_publication=TEST_ARTICLE_PUBLICATION,
    )

    # Assert
    assert item.number == 1
    assert item.name == TEST_ITEM_TEXT
    assert item.article_url == TEST_ARTICLE_URL


def test_news_item():
    # Arrange
    item = episode_segments.NewsItem(item_number=1, topic=TEST_TOPIC, url=TEST_ARTICLE_URL)

    # Assert
    assert item.item_number == 1
    assert item.topic == TEST_TOPIC
    assert item.url == TEST_ARTICLE_URL


def test_news_meta_segment():
    # Arrange
    news_topic = "News 1"

    news_items = [
        episode_segments.NewsItem(item_number=1, topic=news_topic, url=f"{TEST_ARTICLE_URL}1"),
        episode_segments.NewsItem(item_number=2, topic="News 2", url=f"{TEST_ARTICLE_URL}2"),
    ]

    # Act
    segment = episode_segments.NewsMetaSegment(news_segments=news_items)

    # Assert
    assert len(segment.news_segments) == 2
    assert segment.news_segments[0].topic == news_topic


def test_interview_segment():
    # Arrange/Act
    segment = episode_segments.InterviewSegment(name=TEST_ATTRIBUTION, url=TEST_ARTICLE_URL)

    # Assert
    assert segment.name == TEST_ATTRIBUTION
    assert segment.url == TEST_ARTICLE_URL


def test_email_segment():
    # Arrange
    test_items = ["Email 1", "Email 2"]

    # Act
    segment = episode_segments.EmailSegment(items=test_items)

    # Assert
    assert len(segment.items) == 2
    assert test_items[0] in segment.items


def test_quote_segment():
    # Arrange/Act
    segment = episode_segments.QuoteSegment(quote=TEST_QUOTE, attribution=TEST_ATTRIBUTION)

    # Assert
    assert segment.quote == TEST_QUOTE
    assert segment.attribution == TEST_ATTRIBUTION


def test_whats_the_word_segment():
    # Arrange
    test_word = "test"

    # Act
    segment = episode_segments.WhatsTheWordSegment(word=test_word)

    # Assert
    assert segment.word == test_word


def test_logical_fallacy_segment():
    # Arrange
    test_fallacy = "Ad Hominem"

    # Act
    segment = episode_segments.LogicalFallacySegment(topic=test_fallacy)

    # Assert
    assert segment.topic == test_fallacy


def test_quickie_segment():
    # Arrange/Act
    title = "Quick News"
    subject = "Science"
    segment = episode_segments.QuickieSegment(title=title, subject=subject, url=TEST_ARTICLE_URL)

    # Assert
    assert segment.title == title
    assert segment.subject == subject
    assert segment.url == TEST_ARTICLE_URL


def test_tiktok_segment():
    # Arrange
    test_tiktok_url = "http://tiktok.com/test"
    test_tiktok_title = "Test TikTok"

    # Act
    segment = episode_segments.TikTokSegment(title=test_tiktok_title, url=test_tiktok_url)

    # Assert
    assert segment.title == test_tiktok_title
    assert segment.url == test_tiktok_url


def test_dumbest_thing_segment():
    # Arrange/Act
    segment = episode_segments.DumbestThingOfTheWeekSegment(topic=TEST_TOPIC, url=TEST_ARTICLE_URL)

    # Assert
    assert segment.topic == TEST_TOPIC
    assert segment.url == TEST_ARTICLE_URL


def test_noisy_segment():
    # Act
    segment = episode_segments.NoisySegment()

    # Assert
    assert segment.last_week_answer == "<!-- Failed to extract last week's answer -->"


def test_forgotten_superheroes_segment():
    # Act
    segment = episode_segments.ForgottenSuperheroesOfScienceSegment()

    # Assert
    assert segment.subject == "N/A<!-- Failed to extract subject -->"


def test_swindlers_list_segment():
    # Act
    segment = episode_segments.SwindlersListSegment(url=None)

    # Assert
    assert segment.topic == "N/A<!-- Failed to extract topic -->"
