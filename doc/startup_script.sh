#! /bin/bash
cd "$HOME"/transcription-bot && \
git reset --hard && \
git pull && \
"$HOME"/.local/bin/poetry install --sync && \
"$HOME"/.local/bin/poetry run python transcription_bot/main.py ; \
sudo shutdown -h now
