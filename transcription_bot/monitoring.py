import functools
from typing import TYPE_CHECKING, ParamSpec, TypeVar

import cronitor

from transcription_bot.config import CRONITOR_API_KEY, CRONITOR_JOB_ID, IN_GCP

if TYPE_CHECKING:
    from collections.abc import Callable


P = ParamSpec("P")
R = TypeVar("R")

if IN_GCP and (not CRONITOR_API_KEY or not CRONITOR_JOB_ID):
    raise ValueError("Missing env var CRONITOR_API_KEY")


def monitor_run(func: "Callable[P, R]") -> "Callable[P, R]":
    """Perform monitoring of the decorated function."""

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        _signal_start()

        try:
            result = func(*args, **kwargs)
        except:
            _signal_failure()
            raise
        else:
            _signal_success()

        return result

    return wrapper


def _signal_start() -> None:
    if IN_GCP:
        cronitor.Monitor(CRONITOR_JOB_ID, api_key=CRONITOR_API_KEY).ping(state="run")


def _signal_success() -> None:
    if IN_GCP:
        cronitor.Monitor(CRONITOR_JOB_ID, api_key=CRONITOR_API_KEY).ping(state="complete")


def _signal_failure() -> None:
    if IN_GCP:
        cronitor.Monitor(CRONITOR_JOB_ID, api_key=CRONITOR_API_KEY).ping(state="fail")
