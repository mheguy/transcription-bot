import json
import os
from pathlib import Path

import ngrok
import requests
from dotenv import load_dotenv
from flask import Flask, Response, request, send_file

from sgu.config import SERVER_PORT

load_dotenv()

PYANNOTE_TOKEN = os.environ["PYANNOTE_TOKEN"]
NGROK_TOKEN = os.environ["NGROK_TOKEN"]
VOICEPRINTS_FOLDER = Path("data/voiceprins")

HEADERS = {"Authorization": f"Bearer {PYANNOTE_TOKEN}", "Content-Type": "application/json"}
PYANNOTE_ENDPOINT = "https://api.pyannote.ai/v1/voiceprint"


app = Flask(__name__)


@app.route("/{<str:filename>}", methods=["GET"])
def get_audio_file(filename: str) -> Response:
    return send_file(VOICEPRINTS_FOLDER / filename, mimetype="audio/mpeg")


@app.route("/webhook", methods=["POST"])
def handle_webhook() -> Response:
    data = request.json
    if data is None:
        return Response(status=400)

    job_id = data["jobId"]
    file = VOICEPRINTS_FOLDER / f"{job_id}.json"
    file.write_text(json.dumps(data))

    return Response(status=200)


def send_voiceprints(url: str) -> None:
    webhook_url = f"{url}/webhook"
    for file in VOICEPRINTS_FOLDER.glob("*.mp3"):
        file_url = f"{webhook_url}/{file.name}"
        data = {"webhook": webhook_url, "url": file_url}
        response = requests.post(url, headers=HEADERS, json=data, timeout=10)

        print(response.json())


if __name__ == "__main__":
    listener = ngrok.forward(SERVER_PORT, authtoken=NGROK_TOKEN)
    url = listener.url()

    # Start app and start main
    app.run(port=SERVER_PORT)
    send_voiceprints(url)
