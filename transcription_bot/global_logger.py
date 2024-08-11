import sys

from loguru import logger

from transcription_bot.config import IN_GCP, LOG_LEVEL

logger.remove()


if IN_GCP:
    logger.add(
        sys.stdout,
        format="[transcript-bot] - {level: <8} - {message}",
        level=LOG_LEVEL,
        colorize=False,
    )
else:
    logger.add(
        sys.stdout,
        format="{time:HH:mm:ss} <level>{level: <8}</level> [transcript-bot] {message}",
        level=LOG_LEVEL,
        colorize=True,
    )
