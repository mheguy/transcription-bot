import pickle
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pyannote.audio.pipelines.utils.hook import ProgressHook

from sgu_tool.config import DATA_FOLDER, DIARIZATION_FOLDER, EPISODE_FOLDER, TRANSCRIPTION_FOLDER

if TYPE_CHECKING:
    from pathlib import Path

    from httpx import AsyncClient
    from pyannote.audio import Pipeline
    from pyannote.core import Annotation
    from whisper import Whisper

    from sgu_tool.custom_types import Transcription

RSS_FILE = DATA_FOLDER / "rss.xml"
SIX_DAYS = 60 * 60 * 24 * 6
FILE_SIZE_CUTOFF = 100_000


@dataclass
class Episode:
    episode_number: int
    download_url: str
    expected_file_size: int

    def __post_init__(self) -> None:
        if self.audio_file.exists() and self.audio_file.stat().st_size < FILE_SIZE_CUTOFF:
            raise RuntimeError(f"File size too small for episode #{self.episode_number}")

    @property
    def audio_file(self) -> "Path":
        return EPISODE_FOLDER / f"{self.episode_number:04}.mp3"

    @property
    def transcription_file(self) -> "Path":
        return TRANSCRIPTION_FOLDER / f"{self.episode_number:04}.pkl"

    @property
    def diarization_file(self) -> "Path":
        return DIARIZATION_FOLDER / f"{self.episode_number:04}.pkl"

    async def try_download_audio(self, client: "AsyncClient") -> None:
        if self.audio_file.exists():
            return

        print(f"Downloading episode: {self.episode_number}..")

        resp = await client.get(self.download_url, timeout=3600)
        resp.raise_for_status()
        self.audio_file.write_bytes(resp.content)

        if self.audio_file.stat().st_size < FILE_SIZE_CUTOFF:
            raise RuntimeError(f"Size too small for episode {self.episode_number} (file contains an error message)")

        print(f"Downloaded episode: {self.episode_number}.")

    def get_transcription(self, whisper_model: "Whisper") -> "Transcription":
        if self.transcription_file.exists():
            with self.transcription_file.open("rb") as f:
                return pickle.load(f)  # noqa: S301

        return self.create_transcription(whisper_model)

    def create_transcription(self, whisper_model: "Whisper") -> "Transcription":
        print(f"Creating transcription for episode: {self.episode_number}..")

        start = time.time()
        transcription = whisper_model.transcribe(str(self.audio_file), language="en", verbose=True)
        end = time.time()

        self.transcription_file.write_bytes(pickle.dumps(transcription))

        print(f"Created transcription for episode: {self.episode_number} in {end - start:.2f} seconds.")
        return transcription  # type: ignore

    def get_diarization(self, pipeline: "Pipeline") -> "Annotation":
        if self.diarization_file.exists():
            with self.diarization_file.open("rb") as f:
                return pickle.load(f)  # noqa: S301

        return self.create_diarization(pipeline)

    def create_diarization(self, pipeline: "Pipeline") -> "Annotation":
        print(f"Creating diarization for episode: {self.episode_number}..")

        with ProgressHook() as hook:
            start = time.time()
            diarization: Annotation = pipeline(self.audio_file, hook=hook)
        end = time.time()

        self.diarization_file.write_bytes(pickle.dumps(diarization))

        print(f"Created diarization for episode: {self.episode_number} in {end - start:.2f} seconds.")
        return diarization
