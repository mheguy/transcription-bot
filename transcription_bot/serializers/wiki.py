from transcription_bot.models.episode_data import EpisodeData
from transcription_bot.models.episode_segments import QuoteSegment
from transcription_bot.utils.helpers import get_first_segment_of_type
from transcription_bot.utils.templating import get_template


def create_podcast_wiki_page(episode_data: EpisodeData) -> str:
    """Creates a wiki page for a podcast episode.

    This function gathers all the necessary data for the episode, merges the data into segments,
    and converts the segments into wiki page content.
    """
    episode_metadata = episode_data.metadata
    segment_text = "\n".join(s.to_wiki() for s in episode_data.segments)

    rogues = {s["speaker"].lower() for s in episode_data.transcript}

    qotw_segment = get_first_segment_of_type(episode_data.segments, QuoteSegment)

    template = get_template("base")

    num = str(episode_metadata.podcast.episode_number)
    episode_group_number = num[0] + "0" * (len(num) - 1) + "s"

    if qotw_segment:
        quote_of_the_week = qotw_segment.quote
        quote_of_the_week_attribution = qotw_segment.attribution
    else:
        quote_of_the_week = ""
        quote_of_the_week_attribution = ""

    return template.render(
        segment_text=segment_text,
        episode_number=episode_metadata.podcast.episode_number,
        episode_group_number=episode_group_number,
        episode_icon_name=episode_metadata.image.name,
        episode_icon_caption=episode_metadata.image.caption,
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
    )