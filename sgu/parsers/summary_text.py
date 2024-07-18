from sgu.segments import SPECIAL_SUMMARY_PATTERNS, BaseSegment, UnknownSegment, segment_mapping


def is_special_summary_text(text: str) -> bool:
    """Check if the text indicates something about the episode (guest, live, etc.)."""
    return any(pattern in text for pattern in SPECIAL_SUMMARY_PATTERNS)


def create_segment_from_summary_text(text: str) -> "BaseSegment|None":
    lower_text = text.lower()

    for segment_class in segment_mapping["from_summary"]:
        if segment_class.match_string(lower_text):
            return segment_class.from_summary_text(text)

    for segment_class in segment_mapping["from_notes"]:
        if segment_class.match_string(lower_text):
            return None

    if is_special_summary_text(lower_text):
        return None

    return UnknownSegment(text, "summary")
