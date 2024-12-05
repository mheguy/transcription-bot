"""Perform maintenance of the wiki.

Check the most recently updated episode pages and update the episode list to match the current state of the episodes.
"""

import sentry_sdk
from mutagen.id3._util import ID3NoHeaderError
from mwparserfromhell.nodes.template import Template
from mwparserfromhell.wikicode import Wikicode

from transcription_bot.config import config
from transcription_bot.converters.episode_data_to_segments import convert_episode_data_to_episode_segments
from transcription_bot.data_gathering import gather_metadata
from transcription_bot.data_models import EpisodeStatus, PodcastRssEntry, SguListEntry
from transcription_bot.episode_segments import (
    BaseSegment,
    InterviewSegment,
    NonNewsSegmentMixin,
    ScienceOrFictionSegment,
    get_first_segment_of_type,
)
from transcription_bot.exceptions import NoLyricsTagError
from transcription_bot.global_http_client import http_client
from transcription_bot.global_logger import init_logging, logger
from transcription_bot.helpers import filter_bad_episodes
from transcription_bot.parsers.rss_feed import get_podcast_rss_entries, get_recently_modified_episode_numbers
from transcription_bot.wiki import (
    get_episode_entry_from_list,
    get_episode_list_wiki_page,
    get_episode_template_from_list,
    get_episode_wiki_page,
    update_episode_list,
)

if not config.local_mode:
    sentry_sdk.init(dsn=config.sentry_dsn, environment="production")


def main() -> None:
    """Update wiki episode lists."""
    init_logging()
    config.validators.validate_all()

    logger.info("Getting recently modified episode wiki pages...")
    episode_numbers = get_recently_modified_episode_numbers(http_client)
    logger.info(f"Found {len(episode_numbers)} modified episode pages")

    if not episode_numbers:
        logger.info("No modified episode pages found. Exiting.")
        return

    good_episode_numbers = filter_bad_episodes(episode_numbers)

    logger.info("Getting episodes from podcast RSS feed...")
    rss_map = {episode.episode_number: episode for episode in get_podcast_rss_entries(http_client)}

    logger.info("Getting episode list pages...")
    episode_years = {episode_number: rss_map[episode_number].year for episode_number in good_episode_numbers}
    episode_lists = {year: get_episode_list_wiki_page(year) for year in set(episode_years.values())}

    for episode_number in good_episode_numbers:
        logger.info(f"Processing episode #{episode_number}")

        episode_rss_entry = rss_map[episode_number]

        try:
            process_episode(episode_rss_entry, episode_lists[episode_rss_entry.year])
        except ID3NoHeaderError:
            logger.error(f"Unable to process mp3 for episode {episode_number}")
        except NoLyricsTagError:
            logger.error(f"Cannot process episode {episode_number} due to missing lyrics tag.")

    for year, episode_list in episode_lists.items():
        update_episode_list(http_client, year, str(episode_list))


def process_episode(episode_rss_entry: PodcastRssEntry, episode_list_page: Wikicode) -> None:
    """Update the episode list based on the information about an episode."""
    current_episode_entry = get_episode_entry_from_list(episode_list_page, str(episode_rss_entry.episode_number))
    expected_episode_entry = create_expected_episode_entry(episode_rss_entry)

    if current_episode_entry:
        expected_episode_entry = expected_episode_entry | current_episode_entry

    logger.info("Updating episode entry...")
    create_or_update_episode_entry(episode_list_page, expected_episode_entry)
    logger.info(f"Entry created/updated for episode {episode_rss_entry.episode_number}")


def create_expected_episode_entry(episode_rss_entry: PodcastRssEntry) -> SguListEntry:
    """Construct an episode entry based on the contents of the episode page."""
    episode_number = episode_rss_entry.episode_number
    episode_page = get_episode_wiki_page(episode_number)
    date = episode_rss_entry.date.strftime("%m-%d")
    status = get_episode_status(episode_page)

    logger.debug("Gathering episode metadata...")
    episode_metadata = gather_metadata(episode_rss_entry, http_client)

    logger.debug("Converting data to segments...")
    episode_segments = convert_episode_data_to_episode_segments(episode_metadata)

    return SguListEntry(
        str(episode_number),
        date,
        status,
        other=get_other_segments(episode_number, episode_segments),
        theme=get_sof_theme(episode_number, episode_segments),
        interviewee=get_interviewee(episode_number, episode_segments),
        rogue=None,
    )


def get_episode_status(episode_page: Wikicode) -> EpisodeStatus:
    """Get the status of a transcript."""
    templates: list[Template] = episode_page.filter_templates()

    for template in templates:
        if template.name.strip_code().strip() == "transcription-bot":
            return EpisodeStatus.BOT

    for template in templates:
        if template.name.strip_code().strip() == "Editing required":
            if (
                template.has("transcription")
                and template.get("transcription").value.strip_code().strip().lower() == "y"
            ):
                return EpisodeStatus.OPEN

            if template.has("proofreading") and template.get("proofreading").value.strip_code().strip().lower() == "y":
                return EpisodeStatus.PROOFREAD

            return EpisodeStatus.UNKNOWN

    return EpisodeStatus.UNKNOWN


def create_or_update_episode_entry(episode_list: Wikicode, expected_entry: SguListEntry) -> None:
    """Create or update the entry in the episode list."""
    template = get_episode_template_from_list(episode_list, expected_entry.episode)

    if template is None:
        previous_episode_number = str(int(expected_entry.episode) - 1)

        previous_episode_template = get_episode_template_from_list(episode_list, previous_episode_number)
        if previous_episode_template is None:
            raise ValueError("Trying to create entry, but previous episode not found.")

        template = Template(SguListEntry.identifier)

        # We use insert_before to be higher on the list (later episodes first)
        episode_list.insert_before(previous_episode_template, template)

    expected_entry.update_template(template)


def get_other_segments(episode_number: int, segments: list[BaseSegment]) -> str:
    """Return segments for inclusion in the wiki list's "other" section."""
    anchors = [
        f"[[SGU Episode {episode_number}#{segment.wiki_anchor_tag}|{segment.title}]]"
        for segment in segments
        if isinstance(segment, NonNewsSegmentMixin)
    ]

    if not anchors:
        return "n"

    return "<br>".join(anchors)


def get_sof_theme(episode_number: int, segments: list[BaseSegment]) -> str:
    """Return the SoF theme or "n" for no theme."""
    if (segment := get_first_segment_of_type(segments, ScienceOrFictionSegment)) and segment.theme:
        return f"[[SGU Episode {episode_number}#{segment.wiki_anchor_tag}|{segment.theme}]]"

    return "n"


def get_interviewee(episode_number: int, segments: list[BaseSegment]) -> str:
    """Return the name of the interviewee, or "n" if no interview."""
    if (segment := get_first_segment_of_type(segments, InterviewSegment)) and segment.name:
        return f"[[SGU Episode {episode_number}#{segment.wiki_anchor_tag}|{segment.name}]]"

    return "n"


if __name__ == "__main__":
    main()
