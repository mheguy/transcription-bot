import importlib.resources as pkg_resources
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# General
RUNNING_IN_LOCAL = bool(os.getenv("TB_LOCAL"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG").upper()

# Cronitor
CRONITOR_API_KEY = ""
CRONITOR_JOB_KEY = ""

os.environ["CRONITOR_API_KEY"]
os.environ["CRONITOR_JOB_KEY"]

# Sentry
SENTRY_DSN = os.environ["SENTRY_DSN"]

# Podcast RSS feed
RSS_URL = "https://feed.theskepticsguide.org/feed/rss.aspx?feed=sgu"

# Wiki
WIKI_USERNAME = os.environ["WIKI_USERNAME"]
WIKI_PASSWORD = os.environ["WIKI_PASSWORD"]
WIKI_EPISODE_URL_BASE = "https://www.sgutranscripts.org/w/rest.php/v1/page/SGU_Episode_"
WIKI_API_BASE = "https://sgutranscripts.org/w/api.php"

# Azure info
AZURE_SUBSCRIPTION_KEY = os.environ["AZURE_SUBSCRIPTION_KEY"]
AZURE_SERVICE_REGION = os.environ["AZURE_SERVICE_REGION"]

# Diarization tokens
PYANNOTE_TOKEN = os.environ["PYANNOTE_TOKEN"]
NGROK_TOKEN = os.environ["NGROK_TOKEN"]
PYANNOTE_IDENTIFY_ENDPOINT = "https://api.pyannote.ai/v1/identify"
PYANNOTE_VOICEPRINT_ENDPOINT = "https://api.pyannote.ai/v1/voiceprint"
SERVER_PORT = 23500

# OpenAI
OPENAI_ORG = os.environ["OPENAI_ORGANIZATION"]
OPENAI_PROJECT = os.environ["OPENAI_PROJECT"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
LLM_MODEL = "gpt-4o-mini"

# Internal data paths
DATA_FOLDER = Path(str(pkg_resources.files("transcription_bot").joinpath("data")))
VOICEPRINT_FILE = DATA_FOLDER / "voiceprint_map.json"
TEMPLATES_FOLDER = DATA_FOLDER / "templates"

# Temp data paths
TEMP_DATA_FOLDER = Path("data/").resolve()
TEMP_DATA_FOLDER.mkdir(exist_ok=True)

AUDIO_FOLDER = TEMP_DATA_FOLDER / "audio"
AUDIO_FOLDER.mkdir(exist_ok=True)

CACHE_FOLDER = TEMP_DATA_FOLDER / "cache"
CACHE_FOLDER.mkdir(exist_ok=True)

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
