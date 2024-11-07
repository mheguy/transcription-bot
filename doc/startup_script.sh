#! /bin/bash
set -x

export CRONITOR_API_KEY="API_KEY_HERE"
export CRONITOR_JOB_KEY="ptDp2a"
export SENTRY_DSN="DSN_HERE"
export IN_GCP=1

MONITOR_URL='URL_HERE'
curl $MONITOR_URL?state=run

# shellcheck disable=SC2164
cd /root/transcription-bot

git reset --hard
git pull --ff-only

/root/.local/bin/poetry install --sync

if ! /root/.local/bin/poetry run python transcription_bot/main.py
then
    curl $MONITOR_URL?state=fail
fi

sudo shutdown -h now
