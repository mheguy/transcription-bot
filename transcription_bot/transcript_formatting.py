from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from transcription_bot.transcription import DiarizedTranscript


def format_transcript_for_wiki(transcript: "DiarizedTranscript") -> str:
    """Format the transcript for the wiki."""
    transcript = _trim_whitespace(transcript)
    transcript = _join_speaker_segments(transcript)
    _abbreviate_speakers(transcript)

    text_segments = [
        f"'''{transcript_chunk['speaker']}''':{transcript_chunk['text']}" for transcript_chunk in transcript
    ]

    return "\n\n".join(text_segments)


def format_time(time: float | None) -> str:
    """Format a float time to h:mm:ss or mm:ss if < 1 hour."""
    if not time:
        return "???"

    hour_count = int(time) // 3600

    hour = ""
    if hour_count:
        hour = f"{hour_count}:"

    minutes = f"{int(time) // 60 % 60:02d}:"
    seconds = f"{int(time) % 60:02d}"

    return f"{hour}{minutes}{seconds}"


def adjust_transcript_for_voiceover(complete_transcript: "DiarizedTranscript") -> None:
    """Adjust the transcript for voiceover."""
    voiceover = complete_transcript[0]["speaker"]

    if "SPEAKER_" not in voiceover:
        return

    for chunk in complete_transcript:
        if chunk["speaker"] == voiceover:
            chunk["speaker"] = "Voiceover"


def _trim_whitespace(transcript: "DiarizedTranscript") -> "DiarizedTranscript":
    for chunk in transcript:
        chunk["text"] = chunk["text"].strip()

    return transcript


def _join_speaker_segments(transcript: "DiarizedTranscript") -> "DiarizedTranscript":
    current_speaker = None

    speaker_chunks = []
    for chunk in transcript:
        if chunk["speaker"] != current_speaker:
            speaker_chunks.append(chunk)
            current_speaker = chunk["speaker"]
        else:
            speaker_chunks[-1]["text"] += " " + chunk["text"]
            speaker_chunks[-1]["end"] = chunk["end"]

    return speaker_chunks


def _abbreviate_speakers(transcript: "DiarizedTranscript") -> None:
    for chunk in transcript:
        if chunk["speaker"] == "Voiceover":
            continue

        if "SPEAKER_" in chunk["speaker"]:
            name = "US#" + chunk["speaker"].split("_")[1]
            chunk["speaker"] = name
        else:
            chunk["speaker"] = chunk["speaker"][0]
