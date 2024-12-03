import functools
import json
import pickle
from pathlib import Path
from typing import TYPE_CHECKING, Any, Concatenate, ParamSpec, Protocol, TypeVar

from transcription_bot.config import config
from transcription_bot.global_logger import logger

if TYPE_CHECKING:
    from collections.abc import Callable

    from transcription_bot.data_models import DiarizedTranscript
    from transcription_bot.episode_segments import BaseSegment

P = ParamSpec("P")
R = TypeVar("R")
T = TypeVar("T", bound="HasEpisodeNumber")
Url = str
UrlCache = dict[Url, str]

_TEMP_DATA_FOLDER = Path("data/").resolve()
_CACHE_FOLDER = _TEMP_DATA_FOLDER / "cache"


class HasEpisodeNumber(Protocol):
    """A protocol that requires an episode number."""

    episode_number: int


def cache_for_episode(
    func: "Callable[Concatenate[T, P], R]",
) -> "Callable[Concatenate[T, P], R]":
    """Cache the result of the decorated function to a file.

    Requires the first positional argument be a PodcastEpisode.
    """

    @functools.wraps(func)
    def wrapper(podcast_episode: "T", *args: P.args, **kwargs: P.kwargs) -> R:
        function_dir = _get_cache_dir(func)
        cache_filepath = function_dir / f"{podcast_episode.episode_number}.json_or_pkl"

        if cache_filepath.exists():
            logger.info(f"Using cache for func: {func.__name__}, ep: {podcast_episode.episode_number}")
            return _load_cache(cache_filepath)

        result = func(podcast_episode, *args, **kwargs)

        _save_cache(cache_filepath, result)
        return result

    return wrapper


def cache_url_title(func: "Callable[Concatenate[Url, P], str|None]") -> "Callable[Concatenate[Url, P], str|None]":
    """Provide caching for title page lookups."""

    @functools.wraps(func)
    def wrapper(url: Url, *args: P.args, **kwargs: P.kwargs) -> str | None:
        function_dir = _get_cache_dir(func)
        cache_filepath = function_dir / "urls.json_or_pkl"

        url_cache: UrlCache = {}
        if cache_filepath.exists():
            url_cache = _load_cache(cache_filepath)

        if title := url_cache.get(url):
            logger.info(f"Using url cache for: {url}")
            return title

        result = func(url, *args, **kwargs)

        if result:
            url_cache[url] = result
            _save_cache(cache_filepath, url_cache)

        return result

    return wrapper


def cache_llm(
    func: "Callable[[T, BaseSegment, DiarizedTranscript], float | None]",
) -> "Callable[[T, BaseSegment, DiarizedTranscript], float | None]":
    """Provide caching for title page lookups."""

    @functools.wraps(func)
    def wrapper(_podcast_episode: "T", segment: "BaseSegment", transcript: "DiarizedTranscript") -> float | None:
        function_dir = _get_cache_dir(func)
        episode = _podcast_episode.episode_number
        cache_filepath = function_dir / f"{episode}.json_or_pkl"

        segment_type = segment.__class__.__name__
        transcript_start = transcript[0]["start"]

        cache_key = (segment_type, transcript_start)

        llm_cache = {}
        if cache_filepath.exists():
            llm_cache = _load_cache(cache_filepath)

        if start_time := llm_cache.get(cache_key):
            logger.info(f"Using llm cache for segment type:{segment_type}, {transcript_start=}")
            return start_time

        result = func(_podcast_episode, segment, transcript)

        if result:
            llm_cache[cache_key] = result
            _save_cache(cache_filepath, llm_cache)

        return result

    return wrapper


def _get_cache_dir(func: "Callable[..., Any]") -> Path:
    function_dir = _CACHE_FOLDER / func.__module__ / func.__name__

    if config.local_mode:
        _TEMP_DATA_FOLDER.mkdir(exist_ok=True)
        _CACHE_FOLDER.mkdir(exist_ok=True)
        function_dir.mkdir(parents=True, exist_ok=True)

    return function_dir


def _save_cache(file: "Path", data: Any) -> None:
    if not config.local_mode:
        return

    try:
        file.write_text(json.dumps(data))
    except (TypeError, OverflowError):
        file.write_bytes(pickle.dumps(data))


def _load_cache(file: "Path") -> Any:
    try:
        return json.loads(file.read_text())
    except (TypeError, OverflowError, json.JSONDecodeError, UnicodeDecodeError):
        return pickle.loads(file.read_bytes())  # noqa: S301
