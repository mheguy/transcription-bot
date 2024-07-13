import json
import logging
import os
import threading
from pathlib import Path

import ngrok
import requests
from dotenv import load_dotenv
from flask import Flask, Response, request, send_file

from sgu.config import SERVER_PORT

# This determines who is being processed!
ROGUE_TO_PROCESS = "Steven"

AUDIO_FILE = Path(f"data/voiceprints/{ROGUE_TO_PROCESS}.mp3").resolve()
if not AUDIO_FILE.exists():
    raise ValueError("No audio file found.")

OUTPUT_FILE = AUDIO_FILE.with_name(AUDIO_FILE.stem + ".json")

load_dotenv()
PYANNOTE_TOKEN = os.environ["PYANNOTE_TOKEN"]
NGROK_TOKEN = os.environ["NGROK_TOKEN"]
HEADERS = {"Authorization": f"Bearer {PYANNOTE_TOKEN}", "Content-Type": "application/json"}
PYANNOTE_ENDPOINT = "https://api.pyannote.ai/v1/voiceprint"


app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(funcName)s - %(message)s")
logger = logging.getLogger("voiceprint")


@app.route("/files/<string:filename>", methods=["GET"])
def get_audio_file(filename: str) -> Response:
    logger.info("Got request for %s", filename)
    return send_file(AUDIO_FILE, mimetype="audio/mpeg")


@app.route("/webhook", methods=["POST"])
def handle_webhook() -> Response:
    logger.info("Got webhook: %s", request.data)

    data = request.json
    if data is None:
        return Response(status=400)

    OUTPUT_FILE.write_text(json.dumps(data))

    return Response(status=200)


def send_voiceprint(base_url: str) -> None:
    webhook_url = f"{base_url}/webhook"
    file_url = f"{base_url}/files/{AUDIO_FILE.name}"
    data = {"webhook": webhook_url, "url": file_url}

    print(f"{data=}")

    response = requests.post(PYANNOTE_ENDPOINT, headers=HEADERS, json=data, timeout=10)
    response.raise_for_status()

    logger.info("Voiceprint sent. Response: %s", response.content)


if __name__ == "__main__":
    listener = ngrok.forward(SERVER_PORT, authtoken=NGROK_TOKEN)
    url = listener.url()
    logger.info("Listening on %s", url)

    threading.Thread(target=send_voiceprint, args=(url,), daemon=True).start()

    app.run(port=SERVER_PORT)
