import logging

formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(module)s - %(message)s")

handler = logging.StreamHandler()
handler.setFormatter(formatter)

logger = logging.getLogger("sgu")
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)
