import json
import logging
import threading
from pathlib import Path

import ngrok
from dotenv import load_dotenv
from flask import Flask, Response, request, send_file

from sgu.config import AUDIO_FOLDER, DIARIZATION_FOLDER, NGROK_TOKEN, PYANNOTE_TOKEN, SERVER_PORT
from sgu.transcription import send_diarization_request

# This determines who is being processed!
EPOSIDE_TO_PROCESS = "0991"


AUDIO_FILE = AUDIO_FOLDER / f"{EPOSIDE_TO_PROCESS}.mp3"
if not AUDIO_FILE.exists():
    raise ValueError("No audio file found.")

OUTPUT_FILE = DIARIZATION_FOLDER / f"{EPOSIDE_TO_PROCESS}.json"

VOICEPRINT_FILE = Path("sgu/data/voiceprint_map.json").resolve()
if not VOICEPRINT_FILE.exists():
    raise ValueError("No voiceprint file found.")


load_dotenv()
HEADERS = {"Authorization": f"Bearer {PYANNOTE_TOKEN}", "Content-Type": "application/json"}


app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(funcName)s - %(message)s")
logger = logging.getLogger("voiceprint")


@app.route("/files/<string:filename>", methods=["GET"])
def get_audio_file(filename: str) -> Response:
    logger.info("Got request for: %s", filename)
    return send_file(AUDIO_FILE, mimetype="audio/mpeg")


@app.route("/webhook", methods=["POST"])
def handle_webhook() -> Response:
    logger.info("Webhook called with: %s", request.data)

    data = request.json
    if data is None:
        return Response(status=400)

    OUTPUT_FILE.write_text(json.dumps(data))

    return Response(status=200)


if __name__ == "__main__":
    listener = ngrok.forward(SERVER_PORT, authtoken=NGROK_TOKEN)
    url = listener.url()
    logger.info("Listening on %s", url)
    audio_file_url = f"{url}/files/{AUDIO_FILE.name}"

    threading.Thread(target=send_diarization_request, args=(url, audio_file_url), daemon=True).start()

    app.run(port=SERVER_PORT)
