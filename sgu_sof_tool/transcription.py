import pickle
from typing import TYPE_CHECKING, TypedDict

import whisper

from sgu_sof_tool.constants import TRANSCRIPTION_MODEL

if TYPE_CHECKING:
    from sgu_sof_tool.episodes import Episode


class Segment(TypedDict):
    start_time: float
    end_time: float
    text: str


class Transcription(TypedDict):
    text: str
    segments: list[Segment]


def ensure_transcriptions_generated(episodes: list["Episode"]):
    print("Ensuring all episodes have transcription files..")
    whisper_model = whisper.load_model(TRANSCRIPTION_MODEL, device="cuda")

    for episode in episodes:
        if not episode.transcription_file.exists():
            print(f"Transcribing episode: {episode.episode_number}")
            transcription = whisper_model.transcribe(str(episode.audio_file), language="en")

            episode.transcription_file.write_bytes(pickle.dumps(transcription))
            print(f"Transcribed episode: {episode.episode_number}")

    print("All episodes have transcription files.")
