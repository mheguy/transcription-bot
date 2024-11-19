import inspect
import json
import logging
import threading
from pathlib import Path

import ngrok
import requests
from flask import Flask, Response, request, send_file

from transcription_bot.config import config

# This determines who is being processed!
ROGUE_TO_PROCESS = "Steve"

AUDIO_FILE = Path(f"data/voiceprints/{ROGUE_TO_PROCESS}.mp3").resolve()
if not AUDIO_FILE.exists():
    raise ValueError("No audio file found.")

OUTPUT_FILE = AUDIO_FILE.with_name(AUDIO_FILE.stem + ".json")

HEADERS = {"Authorization": f"Bearer {config.pyannote_token}", "Content-Type": "application/json"}
app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(funcName)s - %(message)s")
logger = logging.getLogger("voiceprint")


@app.route("/files/<string:filename>", methods=["GET"])
def get_audio_file(filename: str) -> Response:
    """Flask endpoint to serve the custom audio file."""
    logger.info("Got request for %s", filename)
    return send_file(AUDIO_FILE, mimetype="audio/mpeg")


@app.route("/webhook", methods=["POST"])
def handle_webhook() -> Response:
    """Flask endpoint to handle the webhook."""
    logger.info("Got webhook: %s", request.data)

    data = request.json
    if data is None:
        return Response(status=400)

    OUTPUT_FILE.write_text(json.dumps(data))

    return Response(status=200)


def _send_voiceprint(base_url: str) -> None:
    webhook_url = f"{base_url}/webhook"
    file_url = f"{base_url}/files/{AUDIO_FILE.name}"
    data = {"webhook": webhook_url, "url": file_url}

    logger.info("data=%s", data)

    response = requests.post(config.pyannote_voiceprint_endpoint, headers=HEADERS, json=data, timeout=10)
    response.raise_for_status()

    logger.info("Voiceprint sent. Response: %s", response.content)


if __name__ == "__main__":
    listener = ngrok.forward(config.server_port, authtoken=config.ngrok_token)
    if inspect.isawaitable(listener):
        raise ValueError("ngrok.forward() returned an _asyncio.Task")

    url = listener.url()
    logger.info("Listening on %s", url)

    threading.Thread(target=_send_voiceprint, args=(url,), daemon=True).start()

    app.run(port=config.server_port)
