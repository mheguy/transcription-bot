import sys

from loguru import logger

from transcription_bot.config import LOG_LEVEL

logger.remove()


logger.add(
    sys.stderr,
    format="{time:HH:mm:ss} <level>{level: <8}</level> [transcript-bot] {message}",
    level=LOG_LEVEL,
    colorize=True,
)
