import pytest

from transcription_bot.config import CONFIG_FILE, config


@pytest.fixture(autouse=True, scope="session")
def clean_config() -> None:
    """Disable caching and remove all environment variables for tests (to prevent external calls)."""
    config.validators.clear()
    config.load_file(CONFIG_FILE)


@pytest.fixture()
def enable_local_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """Enable caching for tests."""
    monkeypatch.setattr(config, "local_mode", True)
