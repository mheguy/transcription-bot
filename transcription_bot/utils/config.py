import importlib.resources as pkg_resources
from pathlib import Path
from typing import Any, Protocol, cast

from dynaconf import Dynaconf, Validator
from dynaconf.validator import ValidatorList

# Internal data paths
DATA_FOLDER = Path(str(pkg_resources.files("transcription_bot").joinpath("data")))
VOICEPRINT_FILE = DATA_FOLDER / "voiceprint_map.json"
TEMPLATES_FOLDER = DATA_FOLDER / "templates"
CONFIG_FILE = DATA_FOLDER / "config.toml"

# Episodes that will raise exceptions when processed
UNPROCESSABLE_EPISODES = {
    # No lyrics - episodes 1-208 do not have embedded lyrics
    *range(1, 208 + 1),
    # Episodes that we cannot process
    300,  # Missing news item text
    320,  # News item #3 has unexpected line break
    502,  # News items contains a non-standard item
    875,  # Issue with news items identified as SOF
}


_REQUIRED_ENV_VARS = [
    "wiki_username",
    "wiki_password",
    "azure_subscription_key",
    "azure_service_region",
    "ngrok_token",
    "openai_organization",
    "openai_project",
    "openai_api_key",
    "pyannote_token",
]

_REQUIRED_ONLY_IN_PROD_ENV_VARS = ["sentry_dsn", "cronitor_api_key", "cronitor_job_id"]


class ConfigProto(Protocol):
    """Protocol for config object."""

    # Built-ins
    validators: ValidatorList

    def load_file(  # noqa: D102
        self,
        path: str | Path | None = None,
        env: str | None = None,
        silent: bool = True,  # noqa: FBT001, FBT002
        key: str | None = None,
        validate: Any = None,
    ) -> None: ...

    # Config variables
    local_mode: bool

    # RSS feeds
    podcast_rss_url: str
    wiki_rss_url: str

    # Wiki
    wiki_username: str
    wiki_password: str
    wiki_episode_url_base: str
    wiki_api_base: str

    # Azure / transcription
    azure_subscription_key: str
    azure_service_region: str

    # pyannote / diarization
    pyannote_token: str
    pyannote_identify_endpoint: str
    pyannote_voiceprint_endpoint: str
    pyannote_jobs_endpoint: str

    # Local server
    ngrok_token: str
    server_port: int

    # OpenAI / GPT / llm
    openai_organization: str
    openai_project: str
    openai_api_key: str
    llm_model: str

    # Monitoring (only in deployed)
    sentry_dsn: str
    cronitor_api_key: str
    cronitor_job_id: str


_prod_only_validators = [
    Validator(
        var_name,
        required=True,
        ne="",
        messages={"operations": "{name} must not be blank when in production"},
        when=Validator("local_mode", eq=False),
    )
    for var_name in _REQUIRED_ONLY_IN_PROD_ENV_VARS
]

config = Dynaconf(
    envvar_prefix="TB",
    settings_files=[CONFIG_FILE],
    load_dotenv=True,
    ignore_unknown_envvars=True,
    validators=[
        Validator("log_level", cast=lambda x: x.upper()),
        Validator("local_mode", cast=bool),
    ],
)

config = cast("ConfigProto", config)

config.validators.register(
    *_prod_only_validators,
    *(
        Validator(env_var, required=True, ne="", messages={"operations": "{name} must not be blank"})
        for env_var in _REQUIRED_ENV_VARS
    ),
)
