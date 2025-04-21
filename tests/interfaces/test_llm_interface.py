from pathlib import Path
from unittest.mock import MagicMock, patch

from transcription_bot.interfaces import llm_interface
from transcription_bot.models.episode_segments.base import BaseSegment
from transcription_bot.models.simple_models import DiarizedTranscript

TEST_LLM_RESULT = 42.0


def test_cache_llm(tmp_path: Path, segment: MagicMock, transcript: MagicMock):
    # Arrange
    llm_mock = MagicMock(return_value=TEST_LLM_RESULT)
    episode_num = 332

    with patch("transcription_bot.utils.caching._CACHE_FOLDER", tmp_path):

        @llm_interface.cache_llm_for_segment
        def test_llm(_episode: int, _segment: BaseSegment, _transcript: DiarizedTranscript) -> float:  # noqa: PT019
            return llm_mock(_episode, _segment, _transcript)

        # Act
        # First call - should execute function and cache
        result1 = test_llm(episode_num, segment, transcript)
        # Second call - should use cache
        result2 = test_llm(episode_num, segment, transcript)

        # Assert
        assert result1 == TEST_LLM_RESULT
        assert result2 == result1
        # Verify the underlying function was only called once
        llm_mock.assert_called_once_with(episode_num, segment, transcript)
