import functools
import json
import pickle
from collections.abc import Callable
from pathlib import Path
from typing import Any, Concatenate, ParamSpec, Protocol, TypeVar, cast

from loguru import logger

Url = str
P = ParamSpec("P")
T = TypeVar("T", bound="HasEpisodeNumber")
R = TypeVar("R")
_sentinel = object()

_TEMP_DATA_FOLDER = Path("data/").resolve()
_CACHE_FOLDER = _TEMP_DATA_FOLDER / "cache"


class HasEpisodeNumber(Protocol):
    """A protocol that requires an episode number."""

    episode_number: int


def cache_for_episode(
    func: Callable[Concatenate[T, P], R] | None = None,
    *,
    should_cache: Callable[[R], bool] = lambda _: True,
) -> Callable[..., Any]:
    """Cache the result of the decorated function to a file.

    Can be used as either a bare decorator:

        @cache_for_episode
        def fn(ep): ...

    Or with a keyword `should_cache` that decides whether a function's return
    value should be saved to cache:

        @cache_for_episode(should_cache=lambda result: bool(result))
        def fn(ep): ...

    The `should_cache` callable accepts the function's return value and returns
    a bool indicating whether that value should be saved to cache.

    The decorated function's first positional argument must expose an `episode_number`.
    """

    def _decorate(func: Callable[Concatenate[T, P], R]) -> Callable[Concatenate[T, P], R]:
        @functools.wraps(func)
        def wrapper(rss_entry: T, *args: P.args, **kwargs: P.kwargs) -> R:
            function_dir = get_cache_dir(func)
            cache_filepath = function_dir / f"{rss_entry.episode_number}.json_or_pkl"

            if cache_filepath.exists():
                logger.info(f"Using cache for func: {func.__name__}, ep: {rss_entry.episode_number}")
                return load_cache(cache_filepath)

            result = func(rss_entry, *args, **kwargs)

            if should_cache(result):
                logger.debug(f"Caching result for func: {func.__name__}, ep: {rss_entry.episode_number}")
                save_cache(cache_filepath, result)
            else:
                logger.debug(f"Not caching result for func: {func.__name__}, ep: {rss_entry.episode_number}")

            return result

        return wrapper

    # Support both usages: @cache_for_episode and @cache_for_episode(should_cache=...)
    if func is None:
        return _decorate

    return _decorate(func)


def cache_for_str_arg[**P, R](func: Callable[Concatenate[Url, P], R]) -> Callable[Concatenate[Url, P], R]:
    """Provide caching for any function that takes a string as the first pos arg."""

    @functools.wraps(func)
    def wrapper(url: Url, *args: P.args, **kwargs: P.kwargs) -> R:
        function_dir = get_cache_dir(func)
        cache_filepath = function_dir / "str_arg_cache.json_or_pkl"

        url_cache: dict[Url, R] = {}
        if cache_filepath.exists():
            url_cache = load_cache(cache_filepath)

        title = url_cache.get(url, _sentinel)

        if title is not _sentinel:
            logger.debug(f"Using url cache for: {url}")
            return cast("R", title)

        result = func(url, *args, **kwargs)

        url_cache[url] = result
        save_cache(cache_filepath, url_cache)

        return result

    return wrapper


def get_cache_dir(func: Callable[..., Any]) -> Path:
    """Get the cache directory for the given function."""
    function_dir = _CACHE_FOLDER / func.__module__ / func.__name__

    _TEMP_DATA_FOLDER.mkdir(exist_ok=True)
    _CACHE_FOLDER.mkdir(exist_ok=True)
    function_dir.mkdir(parents=True, exist_ok=True)

    return function_dir


def save_cache(file: Path, data: Any) -> None:
    """Save data to the cache file."""
    try:
        file.write_text(json.dumps(data))
    except (TypeError, OverflowError):
        file.write_bytes(pickle.dumps(data))


def load_cache(file: Path) -> Any:
    """Load the cache file."""
    try:
        return json.loads(file.read_text())
    except (TypeError, OverflowError, json.JSONDecodeError, UnicodeDecodeError):
        return pickle.loads(file.read_bytes())  # noqa: S301
