from typing import TYPE_CHECKING

from transcription_bot.parsers.lyrics import parse_lyrics
from transcription_bot.parsers.show_notes import parse_show_notes
from transcription_bot.parsers.summary_text import parse_summary_text
from transcription_bot.segment_joiner import join_segments

if TYPE_CHECKING:
    from transcription_bot.data_gathering import EpisodeData
    from transcription_bot.episode_segments import Segments


def convert_episode_data_to_episode_segments(episode_data: "EpisodeData") -> "Segments":
    """Converts episode data into segments.

    This function takes the episode data and parses the lyrics, show notes, and summary text
    into separate segments. It then joins the segments together.

    Args:
        episode_data (EpisodeData): The episode data.

    Returns:
        Segments: The joined segments.
    """
    lyric_segments = parse_lyrics(episode_data.lyrics)
    show_note_segments = parse_show_notes(episode_data.show_notes)
    summary_text_segments = parse_summary_text(episode_data.podcast.summary)

    return join_segments(lyric_segments, show_note_segments, summary_text_segments)
