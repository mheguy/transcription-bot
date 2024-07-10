from dataclasses import dataclass
from io import BytesIO
from typing import TYPE_CHECKING

from mutagen.id3 import ID3

if TYPE_CHECKING:
    from mutagen.id3._frames import USLT


@dataclass
class LyricsData:
    raw_text: str


def process_mp3(raw_bytes: bytes) -> LyricsData:
    raw_lyrics = get_mp3_lyrics(raw_bytes)

    return LyricsData("")


def get_mp3_lyrics(raw_bytes: bytes) -> str:
    audio = ID3(BytesIO(raw_bytes))

    uslt_frame: USLT = audio.getall("USLT::eng")[0]

    result = getattr(uslt_frame, "text", None)

    if result is None:
        raise ValueError("could not find lyrics")

    return result
