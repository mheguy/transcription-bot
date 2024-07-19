import re
from typing import TYPE_CHECKING

from sgu.segment_types import BaseSegment, FromLyricsSegment, Segments, SegmentSource, UnknownSegment, segment_types

if TYPE_CHECKING:
    from sgu.segment_types import BaseSegment


def parse_lyrics(lyrics: str) -> Segments:
    lyrics = lyrics.replace("\r", "\n")
    pattern = r"(Segment #\d.+?)(?=(?:Segment #\d+|$))"
    lyric_chunks = re.findall(pattern, lyrics, re.DOTALL)

    return list(filter(None, [create_segment_from_lyric_chunk(line.strip()) for line in lyric_chunks]))


def create_segment_from_lyric_chunk(text: str) -> "BaseSegment|None":
    match = re.search(r"Segment #(\d+)", text)

    segment_number = int(match.group(1)) if match else 0

    text = re.sub(r"segment #\d+\.?", "", text, flags=re.IGNORECASE).strip()
    match_text = text.lower().strip()

    found_match = False
    for segment_class in segment_types:
        if segment_class.match_string(match_text):
            found_match = True
            if issubclass(segment_class, FromLyricsSegment):
                return segment_class.from_lyrics(text, segment_number)

    if found_match:
        raise ValueError(f"Match found in other parsers: {text}")

    return UnknownSegment(segment_number=segment_number, text=text, source=SegmentSource.LYRICS)
