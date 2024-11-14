import sys

from loguru import logger

from transcription_bot.config import LOG_LEVEL, RUNNING_IN_LOCAL

logger.remove()


if RUNNING_IN_LOCAL:
    logger.add(
        sys.stdout,
        format="{time:HH:mm:ss} <level>{level: <8}</level> [transcript-bot] {message}",
        level=LOG_LEVEL,
        colorize=True,
    )
else:
    logger.add(
        sys.stdout,
        format="[transcript-bot] - {level: <8} - {message}",
        level=LOG_LEVEL,
        colorize=False,
    )
