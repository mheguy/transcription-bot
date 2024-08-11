#! /bin/bash
set -x

MONITOR_URL='URL_HERE'
curl $MONITOR_URL?state=run

# shellcheck disable=SC2164
cd /root/transcription-bot

git reset --hard
git pull --ff-only

/root/.local/bin/poetry install --sync

export IN_GCP=1
if /root/.local/bin/poetry run python transcription_bot/main.py
then
    curl $MONITOR_URL?state=complete
else
    curl $MONITOR_URL?state=fail
fi

sudo shutdown -h now
