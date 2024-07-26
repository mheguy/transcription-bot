import sys

from loguru import logger

from sgu.config import LOG_LEVEL

logger.remove()


logger.add(
    sys.stdout,
    format="{time:HH:mm:ss} <level>{level: <8}</level> [SGU] {message}",
    level=LOG_LEVEL,
    colorize=True,
)
