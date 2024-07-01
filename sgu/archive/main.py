import asyncio
import json

import httpx
from dotenv import load_dotenv

from sgu_tool.custom_types import DiarizedTranscript
from sgu_tool.helpers import (
    ensure_directories,
    extract_rogue_names_from_transcription,
    get_podcast_episodes,
    get_rss_feed_entries,
    load_models,
    merge_transcript_and_diarization,
)

load_dotenv()


async def create_transcription() -> None:
    print("Starting...")
    ensure_directories()
    whisper_model, pipeline, nlp = load_models()

    async with httpx.AsyncClient(follow_redirects=True) as client:
        feed_entries = await get_rss_feed_entries(client)
        episodes = get_podcast_episodes(feed_entries)

        for episode in episodes:
            if episode.has_diarized_transcript:
                continue

            audio_file = await episode.get_audio_file(client)

            transcription = episode.get_transcription(audio_file, whisper_model)
            episode.transcription_file.write_text(json.dumps(transcription))
            print("Transcription saved.")

            rogues = extract_rogue_names_from_transcription(nlp, transcription)
            max_speakers = len(rogues) + 1  # Add 1 for the intro + Sci or Fict voice

            diarization = episode.get_diarization(audio_file, pipeline, max_speakers)
            episode.diarization_file.write_text(json.dumps(diarization))
            print("Diarization saved.")

            diarized_transcript_segments = merge_transcript_and_diarization(transcription, diarization)

            diarized_transcript = DiarizedTranscript(rogues=rogues, segments=diarized_transcript_segments)
            episode.diarized_transcript_file.write_text(json.dumps(diarized_transcript))
            print("Diarized transcript saved.")

            # Next up, trying to tag the speakers with the rogues' names


if __name__ == "__main__":
    asyncio.run(create_transcription())
