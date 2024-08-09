import os
import sys

from loguru import logger

from transcription_bot.config import LOG_LEVEL

logger.remove()

log_format = "{time:HH:mm:ss} <level>{level: <8}</level> [transcript-bot] {message}"

logger.add(
    sys.stderr,
    format=log_format,
    level=LOG_LEVEL,
    colorize=True,
)

if os.getenv("GCE_METADATA_HOST"):
    from logging.handlers import SysLogHandler

    handler = SysLogHandler(address="/dev/log")
    logger.add(handler)
