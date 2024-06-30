import asyncio
import os
import pickle

import httpx
import torch
import whisper
from pyannote.audio import Pipeline

from sgu_tool.config import TRANSCRIPTION_MODEL
from sgu_tool.helpers import (
    ensure_directories,
    get_podcast_episodes,
    get_rss_feed_entries,
    merge_transcript_and_diarization,
    sanitize_mp3_tag,
)


async def main() -> None:
    print("Starting...")
    ensure_directories()

    print("Loading models..")
    gpu = torch.device("cuda")
    whisper_model = whisper.load_model(TRANSCRIPTION_MODEL, device=gpu)
    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1", use_auth_token=os.getenv("HUGGING_FACE_KEY")
    )
    pipeline.to(gpu)
    print("Models loaded.")

    async with httpx.AsyncClient(follow_redirects=True) as client:
        feed_entries = await get_rss_feed_entries(client)
        episodes = get_podcast_episodes(feed_entries)

        for episode in episodes:
            await episode.try_download_audio(client)
            sanitize_mp3_tag(episode.audio_file)

            transcription = episode.get_transcription(whisper_model)

            # TODO: Get some stats from the transcription to feed to diarization (ex. max number of speakers)

            diarization = episode.get_diarization(pipeline)
            diarized_transcript = merge_transcript_and_diarization(transcription, diarization)

            episode.transcription_file.write_bytes(pickle.dumps(diarized_transcript))

            # Maybe upload it somewhere or something?
            break


if __name__ == "__main__":
    asyncio.run(main())
