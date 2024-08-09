import os
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


if os.getenv("GOOGLE_VM_CONFIG_LOCK_FILE"):
    from logging.handlers import SysLogHandler

    handler = SysLogHandler(address="/dev/log")
    logger.add(handler, colorize=False, level=LOG_LEVEL, format="transcribe-bot[0000]: {level: <8} {message}")
