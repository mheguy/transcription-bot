class TranscriptionBotError(Exception):
    """Base class for transcription bot exceptions."""


class NoLyricsTagError(TranscriptionBotError):
    """Exception raised when no lyrics tag is found."""


class StringMatchError(TranscriptionBotError):
    """Exception raised when no match is found in a string."""
