"""Perform maintenance of the wiki.

Check the most recently updated episode pages and update the episode list to match the current state of the episodes.
"""

import time
from typing import TYPE_CHECKING

import requests
import sentry_sdk

from transcription_bot.config import config
from transcription_bot.data_models import EpisodeStatus, SguListEntry
from transcription_bot.global_logger import init_logging, logger
from transcription_bot.helpers import get_year_from_episode_number
from transcription_bot.parsers.rss_feed import (
    PodcastRssEntry,
    get_podcast_rss_entries,
    get_recently_modified_episode_pages,
)
from transcription_bot.wiki import get_episode_entry_from_list, get_episode_list_wiki_page, get_episode_wiki_page

if TYPE_CHECKING:
    import pywikibot

if not config.local_mode:
    sentry_sdk.init(dsn=config.sentry_dsn, environment="production")


def main() -> None:
    """Update wiki episode lists."""
    init_logging()
    config.validators.validate_all()

    http_client = requests.Session()

    logger.info("Getting recently modified episode wiki pages...")
    modified_episode_pages = get_recently_modified_episode_pages(http_client)
    logger.info("Found %d modified episode pages", len(modified_episode_pages))

    logger.info("Getting episodes from podcast RSS feed...")
    rss_entries = get_podcast_rss_entries(http_client)

    for episode_number in modified_episode_pages:
        logger.info(f"Processing episode #{episode_number}")
        episode_rss_entry = next(episode for episode in rss_entries if episode.episode_number == episode_number)
        process_modified_episode_page(episode_rss_entry)


def process_modified_episode_page(episode_rss_entry: PodcastRssEntry) -> None:
    """Process a modified episode page."""
    episode_number = episode_rss_entry.episode_number
    year = get_year_from_episode_number(episode_number)
    current_episode_entry = get_episode_entry_from_list(get_episode_list_wiki_page(year), str(episode_number))

    expected_episode_entry = get_expected_episode_entry(episode_rss_entry)

    print(year, current_episode_entry, expected_episode_entry)


def get_expected_episode_entry(episode_rss_entry: PodcastRssEntry) -> SguListEntry:
    """Construct an episode entry based on the contents of the episode page."""
    episode_number = episode_rss_entry.episode_number
    episode_page = get_episode_wiki_page(episode_number)
    date = time.strftime("%m-%d", episode_rss_entry.published_time)
    status = get_episode_status(episode_page)

    return SguListEntry(
        episode_number,
        date,
        status,
    )


def get_episode_status(episode_page: "pywikibot.Page") -> EpisodeStatus:
    """Get the status of a transcript."""
    for template in episode_page.raw_extracted_templates:
        if template[0] == "transcription-bot":
            return EpisodeStatus.BOT

    for template in episode_page.raw_extracted_templates:
        if template[0] == "Editing required":
            return _get_status_from_editing_template_params(template[1])

    return EpisodeStatus.UNKNOWN


def _get_status_from_editing_template_params(template_params: dict[str, str]) -> EpisodeStatus:
    if template_params.get("transcription") == "yes":
        return EpisodeStatus.OPEN

    if template_params.get("proofreading") == "yes":
        return EpisodeStatus.PROOFREAD

    return EpisodeStatus.UNKNOWN


if __name__ == "__main__":
    main()
