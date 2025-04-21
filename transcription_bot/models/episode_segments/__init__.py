from transcription_bot.models.episode_segments import news, science_or_fiction, simple_segments
from transcription_bot.models.episode_segments.base import (
    FromLyricsSegment,
    FromShowNotesSegment,
    FromSummaryTextSegment,
)

_PARSER_SEGMENT_TYPES = (FromLyricsSegment, FromSummaryTextSegment, FromShowNotesSegment)

# Dynamically populate segment_types with all classes in the modules that extend _PARSER_SEGMENT_TYPES
segment_types = []
for module in (news, science_or_fiction, simple_segments):
    for name in dir(module):
        obj = getattr(module, name)
        if isinstance(obj, type) and issubclass(obj, _PARSER_SEGMENT_TYPES) and obj not in _PARSER_SEGMENT_TYPES:
            segment_types.append(obj)
