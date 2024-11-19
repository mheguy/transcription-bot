import pytest

from transcription_bot import config

REQUIRED_ENV_VARS = [
    "TB_WIKI_USERNAME",
    "TB_WIKI_PASSWORD",
    "TB_AZURE_SUBSCRIPTION_KEY",
    "TB_AZURE_SERVICE_REGION",
    "TB_PYANNOTE_TOKEN",
    "TB_NGROK_TOKEN",
]


@pytest.fixture(autouse=True, scope="session")
def disable_local_mode() -> None:
    """Disable caching for tests."""
    config.config.local_mode = False


@pytest.fixture()
def enable_local_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """Disable caching for tests."""
    monkeypatch.setattr(config.config, "local_mode", True)
