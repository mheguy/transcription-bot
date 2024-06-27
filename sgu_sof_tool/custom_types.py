from typing import TypedDict


class PodcastFeedEntryLink(TypedDict):
    """Only the fields we use."""

    length: str
    href: str


class PodcastFeedEntry(TypedDict):
    """Only the fields we use."""

    title: str
    link: str
    links: list[PodcastFeedEntryLink]
