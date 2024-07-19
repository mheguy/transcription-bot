from urllib.parse import urlparse


def string_is_url(text: str) -> bool:
    parsed = urlparse(text)
    return all([parsed.scheme, parsed.netloc])
