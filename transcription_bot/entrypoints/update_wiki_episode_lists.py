"""Perform maintenance of the wiki.

Check the most recently updated episode pages and update the episode list to match the current state of the episodes.
"""

import time
from typing import TYPE_CHECKING

import sentry_sdk
from mwparserfromhell.nodes.template import Template

from transcription_bot.config import config
from transcription_bot.data_models import EpisodeStatus, SguListEntry
from transcription_bot.global_http_client import http_client
from transcription_bot.global_logger import init_logging, logger
from transcription_bot.helpers import get_year_from_episode_number
from transcription_bot.parsers.rss_feed import (
    PodcastRssEntry,
    get_podcast_rss_entries,
    get_recently_modified_episode_pages,
)
from transcription_bot.wiki import (
    get_episode_entry_from_list,
    get_episode_list_wiki_page,
    get_episode_template_from_list,
    get_episode_wiki_page,
    update_episode_list,
)

if TYPE_CHECKING:
    from mwparserfromhell.wikicode import Wikicode

if not config.local_mode:
    sentry_sdk.init(dsn=config.sentry_dsn, environment="production")


def main() -> None:
    """Update wiki episode lists."""
    init_logging()
    config.validators.validate_all()

    # TODO: Run this against all episodes.

    # logger.info("Getting recently modified episode wiki pages...")
    # modified_episode_pages = get_recently_modified_episode_pages(http_client)
    # logger.info(f"Found {len(modified_episode_pages)} modified episode pages")
    # TODO: Revert this debug code
    modified_episode_pages = [1010]  # TODO: This is a "transcription complete"
    # modified_episode_pages = [1011]  # TODO: This is a "bot"

    logger.info("Getting episodes from podcast RSS feed...")
    rss_entries = get_podcast_rss_entries(http_client)

    for episode_number in modified_episode_pages:
        logger.info(f"Processing episode #{episode_number}")
        episode_rss_entry = next(episode for episode in rss_entries if episode.episode_number == episode_number)
        process_modified_episode_page(episode_rss_entry)


def process_modified_episode_page(episode_rss_entry: PodcastRssEntry) -> None:
    """Process a modified episode page."""
    year = get_year_from_episode_number(episode_rss_entry.episode_number)
    episode_list_page = get_episode_list_wiki_page(year)

    if not episode_list_page:
        raise TypeError(f"Unable to find episode list for year {year}")

    current_episode_entry = get_episode_entry_from_list(episode_list_page, str(episode_rss_entry.episode_number))
    expected_episode_entry = create_expected_episode_entry(episode_rss_entry)

    if current_episode_entry == expected_episode_entry:
        logger.info("Episode entry is already up to date")
    else:
        logger.info("Updating episode entry...")
        create_or_update_episode_entry(year, episode_list_page, expected_episode_entry)


def create_expected_episode_entry(episode_rss_entry: PodcastRssEntry) -> SguListEntry:
    """Construct an episode entry based on the contents of the episode page."""
    episode_number = episode_rss_entry.episode_number
    episode_page = get_episode_wiki_page(episode_number)
    date = time.strftime("%m-%d", episode_rss_entry.published_time)
    status = get_episode_status(episode_page)

    # TODO: Get non-news segments cx
    # TODO: Get sof theme
    # TODO: Get interviewee
    # TODO: Get guest rogue(s)

    return SguListEntry(
        str(episode_number),
        date,
        status,
    )


def get_episode_status(episode_page: "Wikicode") -> EpisodeStatus:
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


def create_or_update_episode_entry(year: int, episode_list: "Wikicode", expected_entry: SguListEntry) -> None:
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

    update_episode_list(http_client, year, str(episode_list))


if __name__ == "__main__":
    main()
