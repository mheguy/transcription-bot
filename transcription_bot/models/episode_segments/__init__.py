from transcription_bot.models.episode_segments.base import (
    FromLyricsSegment,
    FromShowNotesSegment,
    FromSummaryTextSegment,
)

_PARSER_SEGMENT_TYPES = (FromLyricsSegment, FromSummaryTextSegment, FromShowNotesSegment)
segment_types = [
    value
    for value in globals().values()
    if isinstance(value, type) and issubclass(value, _PARSER_SEGMENT_TYPES) and value not in _PARSER_SEGMENT_TYPES
]
