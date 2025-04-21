from transcription_bot.interfaces.llm_interface import get_image_caption_from_llm
from transcription_bot.models.episode_data import EpisodeData
from transcription_bot.models.episode_segments.base import BaseSegment
from transcription_bot.models.episode_segments.simple_segments import QuoteSegment
from transcription_bot.models.simple_models import DiarizedTranscript
from transcription_bot.utils.helpers import format_time, get_first_segment_of_type
from transcription_bot.utils.templating import get_template


def create_podcast_wiki_page(episode_data: EpisodeData, issues: str) -> str:
    """Creates a wiki page for a podcast episode.

    This function gathers all the necessary data for the episode, merges the data into segments,
    and converts the segments into wiki page content.
    """
    episode_raw_data = episode_data.raw_data
    segment_text = "\n".join(convert_segment_to_wiki(s) for s in episode_data.segments)

    rogues = {s["speaker"].lower() for s in episode_data.transcript}

    qotw_segment = get_first_segment_of_type(episode_data.segments, QuoteSegment)

    template = get_template("base")

    num = str(episode_raw_data.rss_entry.episode_number)
    episode_group_number = num[0] + "0" * (len(num) - 1) + "s"

    if qotw_segment:
        quote_of_the_week = qotw_segment.quote
        quote_of_the_week_attribution = qotw_segment.attribution
    else:
        quote_of_the_week = ""
        quote_of_the_week_attribution = ""

    return template.render(
        segment_text=segment_text,
        episode_number=episode_raw_data.rss_entry.episode_number,
        episode_group_number=episode_group_number,
        episode_icon_name=episode_raw_data.image.name,
        episode_icon_caption=get_image_caption_from_llm(episode_raw_data.image.url),
        quote_of_the_week=quote_of_the_week,
        quote_of_the_week_attribution=quote_of_the_week_attribution,
        is_bob_present=("bob" in rogues and "y") or "",
        is_cara_present=("cara" in rogues and "y") or "",
        is_jay_present=("jay" in rogues and "y") or "",
        is_evan_present=("evan" in rogues and "y") or "",
        is_george_present=("george" in rogues and "y") or "",
        is_rebecca_present=("rebecca" in rogues and "y") or "",
        is_perry_present=("perry" in rogues and "y") or "",
        forum_link="",
        issues=issues,
    )


def convert_segment_to_wiki(segment: BaseSegment) -> str:
    """Get the wiki text / section header for the segment."""
    template = get_template(segment.template_name)
    template_values = segment.get_template_values()
    return template.render(
        wiki_anchor=segment.wiki_anchor_tag,
        start_time=format_time(segment.start_time),
        transcript=format_transcript_for_wiki(segment.transcript),
        **template_values,
    )


def format_transcript_for_wiki(transcript: DiarizedTranscript) -> str:
    """Format the transcript for the wiki."""
    transcript = _trim_whitespace(transcript)
    transcript = _join_speaker_transcription_chunks(transcript)
    _abbreviate_speakers(transcript)

    text_chunks = [f"'''{ts_chunk['speaker']}:''' {ts_chunk['text']}" for ts_chunk in transcript]

    return "\n\n".join(text_chunks)


def _abbreviate_speakers(transcript: DiarizedTranscript) -> None:
    for chunk in transcript:
        if chunk["speaker"] == "Voice-over":
            continue

        if "SPEAKER_" in chunk["speaker"]:
            name = "US#" + chunk["speaker"].split("_")[1]
            chunk["speaker"] = name
        else:
            chunk["speaker"] = chunk["speaker"][0]


def _trim_whitespace(transcript: DiarizedTranscript) -> DiarizedTranscript:
    for chunk in transcript:
        chunk["text"] = chunk["text"].strip()

    return transcript


def _join_speaker_transcription_chunks(transcript: DiarizedTranscript) -> DiarizedTranscript:
    current_speaker = None

    speaker_chunks: DiarizedTranscript = []
    for chunk in transcript:
        if chunk["speaker"] != current_speaker:
            speaker_chunks.append(chunk)
            current_speaker = chunk["speaker"]
        else:
            speaker_chunks[-1]["text"] += " " + chunk["text"]
            speaker_chunks[-1]["end"] = chunk["end"]

    return speaker_chunks
