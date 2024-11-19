import sys

from loguru import logger

from transcription_bot.config import ENVIRONMENT, config


def init_logging() -> None:
    """Initialize loguru logger."""
    logger.remove()

    if ENVIRONMENT == "local":
        logger.add(
            sys.stdout,
            format="{time:HH:mm:ss} <level>{level: <8}</level> [transcript-bot] {message}",
            level=config.log_level,
            colorize=True,
        )
    else:
        logger.add(
            sys.stdout,
            format="[transcript-bot] - {level: <8} - {message}",
            level=config.log_level,
            colorize=False,
        )
