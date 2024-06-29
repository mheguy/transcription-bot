from sgu_sof_tool.constants import DATA_FOLDER, DIARIZATION_FOLDER, EPISODE_FOLDER, TRANSCRIPTION_FOLDER


def ensure_directories() -> None:
    """Perform any initial setup."""

    DATA_FOLDER.mkdir(parents=True, exist_ok=True)
    EPISODE_FOLDER.mkdir(parents=True, exist_ok=True)
    TRANSCRIPTION_FOLDER.mkdir(parents=True, exist_ok=True)
    DIARIZATION_FOLDER.mkdir(parents=True, exist_ok=True)
