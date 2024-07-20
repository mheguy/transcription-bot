from sgu.custom_logger import logger
from sgu.segment_types import SPECIAL_SUMMARY_PATTERNS, BaseSegment, FromSummaryTextSegment, Segments, segment_types


def parse_summary_text(summary: str) -> Segments:
    """Parse the summary text and return a list of segments."""
    return list(filter(None, [_create_segment_from_summary_text(line.strip()) for line in summary.split(";")]))


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

    logger.warning("Summary text did not match any segment type: %s", text)
    return None


def _is_special_summary_text(text: str) -> bool:
    return any(pattern in text for pattern in SPECIAL_SUMMARY_PATTERNS)
