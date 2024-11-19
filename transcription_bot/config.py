import importlib.resources as pkg_resources
import os
from pathlib import Path

from dynaconf import Dynaconf, Validator

_required_env_vars = [
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

config = Dynaconf(
    envvar_prefix="TB",
    settings_files=["transcription_bot/data/config.toml"],
    load_dotenv=True,
    ignore_unknown_envvars=True,
    validators=[Validator("log_level", cast=lambda x: x.upper())],
)
config.validators.register(
    *(
        Validator(env_var, required=True, ne="", messages={"operations": "{name} must not be blank"})
        for env_var in _required_env_vars
    )
)

# General
_RUNNING_IN_LOCAL = bool(os.getenv("TB_LOCAL"))
ENVIRONMENT = "local" if _RUNNING_IN_LOCAL else "production"

# Internal data paths
DATA_FOLDER = Path(str(pkg_resources.files("transcription_bot").joinpath("data")))
VOICEPRINT_FILE = DATA_FOLDER / "voiceprint_map.json"
TEMPLATES_FOLDER = DATA_FOLDER / "templates"

# Episodes that will raise exceptions when processed
UNPROCESSABLE_EPISODES = {
    # No lyrics
    *range(1, 208),
    277,
    625,
    652,
    666,
    688,
    741,
    744,
    812,
    862,
    # "Corrupt" episodes
    455,
    471,
    495,
    540,
    772,
}
