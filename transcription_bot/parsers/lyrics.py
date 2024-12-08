import re

from transcription_bot.models.episode_segments import (
    BaseSegment,
    FromLyricsSegment,
    RawSegments,
    UnknownSegment,
    segment_types,
)


def parse_lyrics(lyrics: str) -> RawSegments:
    """Parse the lyrics and return a list of segments."""
    lyrics = lyrics.replace("\r", "\n")
    pattern = r"(Segment #?\d.+?)(?=(?:Segment #?\d+|$))"
    lyric_chunks = re.findall(pattern, lyrics, re.DOTALL)

    return RawSegments(list(filter(None, [_create_segment_from_lyric_chunk(line.strip()) for line in lyric_chunks])))


def _create_segment_from_lyric_chunk(text: str) -> "BaseSegment|None":
    text = re.sub(r"segment #?\d+[-\.:;]?", "", text, flags=re.IGNORECASE).strip()
    match_text = text.lower().strip()

    found_match = False
    for segment_class in segment_types:
        if segment_class.match_string(match_text):
            found_match = True
            if issubclass(segment_class, FromLyricsSegment):
                return segment_class.from_lyrics(text)

    if found_match:
        raise ValueError(f"Match found in other parsers: {text}")

    return UnknownSegment.create(text=text)
