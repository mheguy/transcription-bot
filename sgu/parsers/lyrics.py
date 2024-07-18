import re


def parse_lyrics(lyrics: str):
    lyrics = lyrics.replace("\r", "\n")
    pattern = r"(Segment #\d.+?)(?=(?:Segment #\d+|$))"
    lyric_chunks = re.findall(pattern, lyrics, re.DOTALL)

    for lyric_chunk in lyric_chunks:
        ...
