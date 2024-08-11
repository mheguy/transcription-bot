import os

os.environ["LOG_LEVEL"] = "WARNING"

from time import struct_time

from transcription_bot.config import AUDIO_FOLDER
from transcription_bot.data_gathering import get_lyrics_from_mp3
from transcription_bot.parsers.rss_feed import PodcastEpisode

EPISODES_OF_INTEREST = {
    455,
    471,
    495,
    540,
    772,
}


def main() -> None:
    """Extract lyrics from all episodes."""
    all_files = list(AUDIO_FOLDER.glob("*.mp3"))

    unknown = []
    processed = []
    empties = []
    no_lyrics = []

    if EPISODES_OF_INTEREST:
        all_files = [f for f in all_files if int(f.stem) in EPISODES_OF_INTEREST]

    for f in all_files:
        try:
            file_contents = f.read_bytes()
            if file_contents.startswith(b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"):
                # f.unlink()
                empties.append(int(f.stem))
                continue

            get_lyrics_from_mp3(
                PodcastEpisode(int(f.stem), "", "", "", "", struct_time((0, 0, 0, 0, 0, 0, 0, 0, 0))), file_contents
            )
        except ValueError as e:
            if "Could not find lyrics tag" in str(e) or "Could not find lyrics in tag" in str(e):
                no_lyrics.append(int(f.stem))
            else:
                unknown.append(int(f.stem))
        except Exception:  # noqa: BLE001
            unknown.append(int(f.stem))
        else:
            processed.append(int(f.stem))

    print(f"unknown: {sorted(unknown)}")
    print(f"empty file (no content at all): {sorted(empties)}")
    print(f"no lyrics tag: {sorted(no_lyrics)}")
    print(f"processed correctly: {sorted(processed)}")


if __name__ == "__main__":
    main()
