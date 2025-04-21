from transcription_bot.models.episode_segments import segment_types
from transcription_bot.models.episode_segments.base import BaseSegment, FromSummaryTextSegment
from transcription_bot.models.episode_segments.type_hints import RawSegments


def parse_summary_text(summary: str) -> RawSegments:
    """Parse the summary text and return a list of segments."""
    return RawSegments(
        list(filter(None, [_create_segment_from_summary_text(line.strip()) for line in summary.split(";")]))
    )


def _create_segment_from_summary_text(text: str) -> "BaseSegment|None":
    lower_text = text.lower()

    found_match = False
    for segment_class in segment_types:
        if segment_class.match_string(lower_text):
            found_match = True
            if issubclass(segment_class, FromSummaryTextSegment):
                return segment_class.from_summary_text(text)

    if found_match:
        return None

    if _is_special_summary_text(lower_text):
        return None

    return None


SPECIAL_SUMMARY_PATTERNS = [
    "guest rogue",
    "special guest",
    "live from",
    "live recording",
]


def _is_special_summary_text(text: str) -> bool:
    return any(pattern in text for pattern in SPECIAL_SUMMARY_PATTERNS)
