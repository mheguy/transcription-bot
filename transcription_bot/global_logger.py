import sys

from loguru import logger

from transcription_bot.config import LOG_LEVEL

logger.remove()


logger.add(
    sys.stdout,
    format="{time:HH:mm:ss} <level>{level: <8}</level> [transcript-bot] {message}",
    level=LOG_LEVEL,
    colorize=True,
)
