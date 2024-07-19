import re
from typing import TYPE_CHECKING

from sgu.segment_types import BaseSegment, FromLyricsSegment, Segments, UnknownSegment, segment_types

if TYPE_CHECKING:
    from sgu.segment_types import BaseSegment


def parse_lyrics(lyrics: str) -> Segments:
    lyrics = lyrics.replace("\r", "\n")
    pattern = r"(Segment #\d.+?)(?=(?:Segment #\d+|$))"
    lyric_chunks = re.findall(pattern, lyrics, re.DOTALL)

    return list(filter(None, [create_segment_from_lyrics(line.strip()) for line in lyric_chunks]))


def create_segment_from_lyrics(text: str) -> "BaseSegment|None":
    text = re.sub(r"segment #\d+\.?", "", text, flags=re.IGNORECASE).strip()
    lower_text = text.lower().strip()

    found_match = False
    for segment_class in segment_types:
        if segment_class.match_string(lower_text):
            found_match = True
            if issubclass(segment_class, FromLyricsSegment):
                return segment_class.from_lyrics(text)

    if found_match:
        raise ValueError(f"Match found in other parsers: {text}")

    return UnknownSegment(text, "lyrics")
