import os
from pathlib import Path

# URLs
RSS_URL = "https://feed.theskepticsguide.org/feed/rss.aspx?feed=sgu"
WIKI_EPISODE_URL_BASE = "https://www.sgutranscripts.org/w/rest.php/v1/page/SGU_Episode_"
WIKI_API_BASE = "https://sgutranscripts.org/w/api.php"
PYANNOTE_IDENTIFY_ENDPOINT = "https://api.pyannote.ai/v1/identify"
PYANNOTE_VOICEPRINT_ENDPOINT = "https://api.pyannote.ai/v1/voiceprint"

# Tokens
PYANNOTE_TOKEN = os.environ["PYANNOTE_TOKEN"]
NGROK_TOKEN = os.environ["NGROK_TOKEN"]

# Custom headers to identify ourselves to the SGU servers.
CUSTOM_HEADERS = {"User-Agent": "SGU Wiki Tooling (matthew.heguy@gmail.com)"}

# Server for PyannoteAI callback
SERVER_PORT = 23500

# Transcription settings
TRANSCRIPTION_MODEL = "medium.en"
TRANSCRIPTION_LANGUAGE = "en"
TRANSCRIPTION_PROMPT = "The Skeptic's Guide to the Universe is hosted by Steven Novella, Bob Novella, Jay Novella, Cara Santa Maria, and Evan Bernstein."

# Paths
PROCESSED_DATA_FOLDER = Path("data/").resolve()

TEMPLATES_FOLDER = PROCESSED_DATA_FOLDER / "templates"
VOICEPRINT_FILE = PROCESSED_DATA_FOLDER / "voiceprint_map.json"

AUDIO_FOLDER = PROCESSED_DATA_FOLDER / "audio"
AUDIO_FOLDER.mkdir(exist_ok=True)

DIARIZATION_FOLDER = PROCESSED_DATA_FOLDER / "diarizations"
DIARIZATION_FOLDER.mkdir(exist_ok=True)

CACHE_FOLDER = PROCESSED_DATA_FOLDER / "cache"
CACHE_FOLDER.mkdir(exist_ok=True)
