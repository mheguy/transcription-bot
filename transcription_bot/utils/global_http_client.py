import logging
from typing import Any, cast

import requests
from loguru import logger
from tenacity import before_sleep_log, retry, stop_after_attempt, wait_fixed

__all__ = ["http_client"]

CUSTOM_USER_AGENT = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0"
}
_HTTP_TIMEOUT = 15


class HttpClient(requests.Session):
    def __init__(self):
        super().__init__()
        self.headers.update(CUSTOM_USER_AGENT)

    @staticmethod
    def with_auth_header(header: dict[str, str]) -> "HttpClient":
        client = HttpClient()
        client.headers.update(header)
        return client

    def get(self, *args: Any, **kwargs: Any) -> requests.Response:
        return self._request("GET", *args, **kwargs)

    def post(self, *args: Any, **kwargs: Any) -> requests.Response:
        return self._request("POST", *args, **kwargs)

    def put(self, *args: Any, **kwargs: Any) -> requests.Response:
        return self._request("PUT", *args, **kwargs)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(2),
        reraise=True,
        before_sleep=before_sleep_log(cast(logging.Logger, logger), logging.DEBUG),
    )
    def _request(self, *args: Any, **kwargs: Any) -> requests.Response:
        return self.request(*args, **kwargs, timeout=kwargs.get("timeout", _HTTP_TIMEOUT))


http_client = HttpClient()
