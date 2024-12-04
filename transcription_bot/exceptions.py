class TranscriptionBotError(Exception):
    """Base class for transcription bot exceptions."""


class NoLyricsTagError(TranscriptionBotError):
    """Exception raised when no lyrics tag is found."""
