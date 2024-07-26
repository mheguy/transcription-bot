from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sgu.transcription import DiarizedTranscript


def format_transcript_for_wiki(transcript: "DiarizedTranscript") -> str:
    """Format the transcript for the wiki."""
    transcript = _join_speaker_segments(transcript)
    _abbreviate_speakers(transcript)

    text_segments: list[str] = []
    for transcript_chunk in transcript:
        start_time = _format_time(transcript_chunk["start"])
        end_time = _format_time(transcript_chunk["end"])

        text_segments.append(f"<!-- {start_time} - {end_time} -->")
        text_segments.append(f"'''{transcript_chunk['speaker']}''':{transcript_chunk['text']}<br />")

    return "\n".join(text_segments)


def _format_time(time: float) -> str:
    return f"{int(time) // 3600:02d}:{int(time) // 60 % 60:02d}:{int(time) % 60:02d}"


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
        if "SPEAKER_" in chunk["speaker"]:
            name = "US#" + chunk["speaker"].split("_")[1]
            chunk["speaker"] = name
        else:
            chunk["speaker"] = chunk["speaker"][0]
