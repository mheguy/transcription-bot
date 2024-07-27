from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import TYPE_CHECKING

from mutagen.mp3 import MP3
from pydub import AudioSegment
from tqdm import tqdm

from transcription_bot.config import AUDIO_FOLDER

if TYPE_CHECKING:
    from pathlib import Path

SECONDS_IN_MINUTE = 60
SECONDS_IN_HOUR = 60 * SECONDS_IN_MINUTE
SECONDS_IN_DAY = 24 * SECONDS_IN_HOUR


def format_duration(seconds: float) -> str:
    """Format duration from seconds to hours, minutes, and seconds."""
    seconds = int(seconds)

    days = seconds // SECONDS_IN_DAY
    seconds = seconds % SECONDS_IN_DAY

    hours = seconds // SECONDS_IN_HOUR
    seconds = seconds % SECONDS_IN_HOUR

    minutes = seconds // SECONDS_IN_MINUTE
    seconds = seconds % SECONDS_IN_MINUTE

    return f"{days}d {hours}h {minutes}m {seconds}s"


def process_file(file_path: "Path") -> float:
    """Process a single MP3 file and return its duration."""
    try:
        audio = AudioSegment.from_file(file_path)
    except Exception:  # noqa: BLE001
        print(f"Error processing {file_path.stem} (skipping)")
        return 0.0
    else:
        return len(audio) / 1000.0


def main() -> None:
    """Calculate the total runtime of all MP3 files in the audio folder."""
    total_runtime = 0.0

    all_files = list(AUDIO_FOLDER.glob("*.mp3"))

    remaining_files = []
    for file in tqdm(all_files):
        try:
            audio = MP3(file)
            total_runtime += audio.info.length
        except Exception:  # noqa: BLE001
            remaining_files.append(file)

    remaining_to_process = len(remaining_files)
    print(f"Unable to get duration from metadata for: {remaining_to_process}")

    with ProcessPoolExecutor() as executor:
        print("Processing files as mp3...")
        print("Remaining to process:", remaining_to_process, end="\r")

        futures = [executor.submit(process_file, file_path) for file_path in remaining_files]
        for future in as_completed(futures):
            remaining_to_process -= 1
            print("Remaining to process:", remaining_to_process, end="\r")
            total_runtime += future.result()
        print()

    print(format_duration(total_runtime))


if __name__ == "__main__":
    main()
