from transcription_bot.models.episode_segments import simple_segments
from transcription_bot.models.simple_models import DiarizedTranscript

# Constants for test data
_TEST_ARTICLE_URL = "http://example.com"
_TEST_TOPIC = "Test Topic"
_TEST_QUOTE = "Test quote"
_TEST_ATTRIBUTION = "John Doe"


def test_dumbest_thing_segment():
    # Arrange/Act
    segment = simple_segments.DumbestThingOfTheWeekSegment(topic=_TEST_TOPIC, url=_TEST_ARTICLE_URL)

    # Assert
    assert segment.topic == _TEST_TOPIC
    assert segment.url == _TEST_ARTICLE_URL


def test_email_segment():
    # Arrange
    test_items = ["Email 1", "Email 2"]

    # Act
    segment = simple_segments.EmailSegment(items=test_items)

    # Assert
    assert len(segment.items) == 2
    assert test_items[0] in segment.items


def test_interview_segment():
    # Arrange/Act
    segment = simple_segments.InterviewSegment(name=_TEST_ATTRIBUTION, url=_TEST_ARTICLE_URL)

    # Assert
    assert segment.name == _TEST_ATTRIBUTION
    assert segment.url == _TEST_ARTICLE_URL


def test_intro_segment():
    # Arrange
    diarized_transcript: DiarizedTranscript = [
        {"speaker": "Steve", "text": "Hello everyone", "start": 0.0, "end": 2.0},
        {"speaker": "Bob", "text": "Welcome to the show", "start": 2.0, "end": 4.0},
    ]

    segment = simple_segments.IntroSegment()
    segment.transcript = diarized_transcript
    segment.start_time = segment.get_start_time(diarized_transcript)
    segment.end_time = segment.transcript[-1]["end"]

    # Act
    result = segment.get_start_time(diarized_transcript)

    # Assert
    assert result == 0.0
    assert segment.duration > 0


def test_forgotten_superheroes_segment():
    # Act
    segment = simple_segments.ForgottenSuperheroesOfScienceSegment()

    # Assert
    assert segment.subject == "N/A<!-- Failed to extract subject -->"


def test_logical_fallacy_segment():
    # Arrange
    test_fallacy = "Ad Hominem"

    # Act
    segment = simple_segments.LogicalFallacySegment(topic=test_fallacy)

    # Assert
    assert segment.topic == test_fallacy


def test_noisy_segment():
    # Act
    segment = simple_segments.NoisySegment()

    # Assert
    assert segment.last_week_answer == "<!-- Failed to extract last week's answer -->"


def test_quickie_segment():
    # Arrange/Act
    title = "Quick News"
    subject = "Science"
    segment = simple_segments.QuickieSegment(title=title, subject=subject, url=_TEST_ARTICLE_URL)

    # Assert
    assert segment.title == title
    assert segment.subject == subject
    assert segment.url == _TEST_ARTICLE_URL


def test_quote_segment():
    # Arrange/Act
    segment = simple_segments.QuoteSegment(quote=_TEST_QUOTE, attribution=_TEST_ATTRIBUTION)

    # Assert
    assert segment.quote == _TEST_QUOTE
    assert segment.attribution == _TEST_ATTRIBUTION


def test_swindlers_list_segment():
    # Act
    segment = simple_segments.SwindlersListSegment(url=None)

    # Assert
    assert segment.topic == "N/A<!-- Failed to extract topic -->"


def test_tiktok_segment():
    # Arrange
    test_tiktok_url = "http://tiktok.com/test"
    test_tiktok_title = "Test TikTok"

    # Act
    segment = simple_segments.TikTokSegment(title=test_tiktok_title, url=test_tiktok_url)

    # Assert
    assert segment.title == test_tiktok_title
    assert segment.url == test_tiktok_url


def test_unknown_segment():
    # Arrange
    test_title = "Test Title"
    test_extra = "Extra Info"

    # Act
    segment = simple_segments.UnknownSegment.create(f"{test_title}\n{test_extra}\n{_TEST_ARTICLE_URL}")

    # Assert
    assert segment.title == test_title
    assert segment.extra_text == test_extra
    assert segment.url == _TEST_ARTICLE_URL


def test_whats_the_word_segment():
    # Arrange
    test_word = "test"

    # Act
    segment = simple_segments.WhatsTheWordSegment(word=test_word)

    # Assert
    assert segment.word == test_word
