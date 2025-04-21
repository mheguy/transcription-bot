from transcription_bot.models.simple_models import DiarizedTranscript
from transcription_bot.serializers import wiki


def test_format_transcript_for_wiki():
    # Arrange
    diarized_transcript: DiarizedTranscript = [
        {"speaker": "Steve", "text": "Hello everyone", "start": 0.0, "end": 2.0},
        {"speaker": "Bob", "text": "Welcome to the show", "start": 2.0, "end": 4.0},
    ]

    # Act
    formatted = wiki.format_transcript_for_wiki(diarized_transcript)

    # Assert
    assert "'''S:''' Hello everyone" in formatted
    assert "'''B:''' Welcome to the show" in formatted
