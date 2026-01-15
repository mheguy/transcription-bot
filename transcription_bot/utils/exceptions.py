class TranscriptionBotError(Exception):
    """Base class for transcription bot exceptions."""


class StringMatchError(TranscriptionBotError):
    """Exception raised when no match is found in a string."""


class TranscriptionServiceError(TranscriptionBotError):
    """Exception raised when transcription service fails."""


class DiarizationServiceError(TranscriptionBotError):
    """Exception raised when diarization service fails."""
