import functools
import json
import pickle
from hashlib import sha256
from typing import TYPE_CHECKING, Any, ParamSpec, TypeVar

from sgu.config import CACHE_FOLDER
from sgu.global_logger import logger

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from pathlib import Path

P = ParamSpec("P")
R = TypeVar("R")


def file_cache(func: "Callable[P, R]") -> "Callable[P, R]":
    """Cache the result of the decorated sync function to a file."""

    @functools.wraps(func)
    def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        cache_filepath = _get_cache_file(func, args, kwargs)

        if cache_filepath.exists():
            return _load_cache(cache_filepath)

        result = func(*args, **kwargs)

        _save_cache(cache_filepath, result)
        return result

    return sync_wrapper


def file_cache_async(func: "Callable[P, Coroutine[None, None, R]]") -> "Callable[P, Coroutine[None, None, R]]":
    """Cache the result of the decorated async function to a file."""

    @functools.wraps(func)
    async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        cache_filepath = _get_cache_file(func, args, kwargs)

        if cache_filepath.exists():
            logger.info(f"Loading from cache for: {func.__name__}")
            return _load_cache(cache_filepath)

        result = await func(*args, **kwargs)

        _save_cache(cache_filepath, result)
        return result

    return async_wrapper


def _save_cache(file: "Path", data: Any) -> None:
    try:
        file.write_text(json.dumps(data))
    except (TypeError, OverflowError):
        file.write_bytes(pickle.dumps(data))


def _load_cache(file: "Path") -> Any:
    try:
        return json.loads(file.read_text())
    except (TypeError, OverflowError, json.JSONDecodeError, UnicodeDecodeError):
        return pickle.loads(file.read_bytes())  # noqa: S301


def _get_cache_file(func: "Callable[P, R]", args: Any, kwargs: Any) -> "Path":
    function_dir = CACHE_FOLDER / func.__module__ / func.__name__
    function_dir.mkdir(parents=True, exist_ok=True)

    args_hash = sha256(str(args).encode()).hexdigest()
    kwargs_hash = sha256(str(kwargs).encode()).hexdigest()

    final_hash = sha256(f"{args_hash}_{kwargs_hash}".encode()).hexdigest()

    return function_dir / f"{final_hash}.json_or_pkl"
