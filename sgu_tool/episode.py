# endregion
# region Podcast Episode
import json
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from mutagen.easyid3 import EasyID3
from pyannote.audio.pipelines.utils.hook import ProgressHook

from sgu_tool.config import (
    DIARIZATION_FOLDER,
    DIARIZED_TRANSCRIPT_FOLDER,
    FILE_SIZE_CUTOFF,
    MINIMUM_SPEAKERS,
    TRANSCRIPTION_FOLDER,
)
from sgu_tool.main import (
    TEMP_FOLDER,
)

if TYPE_CHECKING:
    from pathlib import Path

    from httpx import AsyncClient
    from pyannote.audio.pipelines import SpeakerDiarization
    from pyannote.core import Annotation
    from whisper import Whisper

    from sgu_tool.custom_types import Transcription


@dataclass
class PodcastEpisode:
    episode_number: int
    download_url: str

    @property
    def has_diarized_transcript(self) -> bool:
        return self.diarized_transcript_file.exists()

    @property
    def audio_file(self) -> "Path":
        return TEMP_FOLDER / f"{self.episode_number:04}.mp3"

    @property
    def transcription_file(self) -> "Path":
        return TRANSCRIPTION_FOLDER / f"{self.episode_number:04}.json"

    @property
    def diarization_file(self) -> "Path":
        return DIARIZATION_FOLDER / f"{self.episode_number:04}.json"

    @property
    def diarized_transcript_file(self) -> "Path":
        return DIARIZED_TRANSCRIPT_FOLDER / f"{self.episode_number:04}.json"

    async def get_audio_file(self, client: "AsyncClient") -> "Path":
        if self.audio_file.exists():
            return self.audio_file

        await self.download_audio_file(client)
        return self.audio_file

    async def download_audio_file(self, client: "AsyncClient") -> None:
        print(f"Downloading episode: {self.episode_number}..")

        resp = await client.get(self.download_url, timeout=3600)
        resp.raise_for_status()
        self.audio_file.write_bytes(resp.content)

        if self.audio_file.stat().st_size < FILE_SIZE_CUTOFF:
            raise RuntimeError(f"Size too small for episode {self.episode_number} (file contains an error message)")

        self.sanitize_mp3_tag(self.audio_file)

        print(f"Downloaded episode: {self.episode_number}.")

    def get_transcription(self, audio_file: "Path", whisper_model: "Whisper") -> "Transcription":
        if self.transcription_file.exists():
            return json.loads(self.transcription_file.read_text("utf-8"))

        return self.create_transcription(audio_file, whisper_model)

    @staticmethod
    def create_transcription(audio_file: "Path", whisper_model: "Whisper") -> "Transcription":
        print(f"Creating transcription for episode: {audio_file}..")

        start = time.time()
        transcription = whisper_model.transcribe(str(audio_file), language="en", verbose=False)
        end = time.time()

        print(f"Created transcription for episode: {audio_file} in {end - start:.2f} seconds.")
        return transcription  # type: ignore

    def get_diarization(self, audio_file: "Path", pipeline: "SpeakerDiarization", max_speakers: int) -> "Annotation":
        if self.diarization_file.exists():
            return json.loads(self.diarization_file.read_text("utf-8"))

        return self.create_diarization(audio_file, pipeline, max_speakers)

    @staticmethod
    def create_diarization(audio_file: "Path", pipeline: "SpeakerDiarization", max_speakers: int) -> "Annotation":
        print(f"Creating diarization for: {audio_file}..")

        with ProgressHook() as hook:
            start = time.time()
            diarization: Annotation = pipeline(
                audio_file,
                hook=hook,
                min_speakers=MINIMUM_SPEAKERS,
                max_speakers=max_speakers,
            )
        end = time.time()

        print(f"Created diarization for: {audio_file} in {end - start:.2f} seconds.")
        return diarization

    @staticmethod
    def sanitize_mp3_tag(mp3_file: "Path") -> None:
        id3_tag = EasyID3(mp3_file)

        print(f"Removing ID3 tag from: {mp3_file}")
        id3_tag.delete()
        id3_tag.save()
