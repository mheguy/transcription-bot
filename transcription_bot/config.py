import importlib.resources as pkg_resources
from pathlib import Path

from dynaconf import Dynaconf, Validator

# Internal data paths
DATA_FOLDER = Path(str(pkg_resources.files("transcription_bot").joinpath("data")))
VOICEPRINT_FILE = DATA_FOLDER / "voiceprint_map.json"
TEMPLATES_FOLDER = DATA_FOLDER / "templates"
CONFIG_FILE = DATA_FOLDER / "config.toml"

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
config.validators.register(
    *(
        Validator(env_var, required=True, ne="", messages={"operations": "{name} must not be blank"})
        for env_var in _REQUIRED_ENV_VARS
    )
)
