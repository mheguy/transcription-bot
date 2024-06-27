from sgu_sof_tool.constants import DATA_FOLDER, EPISODE_FOLDER


def ensure_directories() -> None:
    """Perform any initial setup."""

    DATA_FOLDER.mkdir(parents=True, exist_ok=True)
    EPISODE_FOLDER.mkdir(parents=True, exist_ok=True)
