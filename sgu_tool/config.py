import os
from pathlib import Path

RSS_URL = "https://feed.theskepticsguide.org/feed/rss.aspx?feed=sgu"
TRANSCRIPTION_MODEL = "medium.en"
MINIMUM_SPEAKERS = 3  # Always at least the intro voice, Steven, and 1 Rogue.

OUTPUT_FOLDER = Path("/storage") if os.getenv("PAPERSPACE_CLUSTER_ID") else Path("data")
TRANSCRIPTION_FOLDER = OUTPUT_FOLDER / "transcriptions"
DIARIZATION_FOLDER = OUTPUT_FOLDER / "diarizations"
DIARIZED_TRANSCRIPT_FOLDER = OUTPUT_FOLDER / "diarized_transcripts"

SIX_DAYS = 60 * 60 * 24 * 6
FILE_SIZE_CUTOFF = 100_000
