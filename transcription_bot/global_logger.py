import sys

from loguru import logger

from transcription_bot.config import IN_GCP, LOG_LEVEL

logger.remove()


if IN_GCP:
    from logging.handlers import SysLogHandler

    handler = SysLogHandler(address="/dev/log")
    logger.add(handler, colorize=False, level=LOG_LEVEL, format="transcribe-bot[0000]: {level: <8} {message}")
else:
    logger.add(
        sys.stderr,
        format="{time:HH:mm:ss} <level>{level: <8}</level> [transcript-bot] {message}",
        level=LOG_LEVEL,
        colorize=True,
    )
