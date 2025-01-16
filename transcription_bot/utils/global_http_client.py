import logging
from typing import Any, override

import requests
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

    @override
    def get(self, *args: Any, raise_for_status: bool = True, **kwargs: Any) -> requests.Response:
        return self._request("GET", *args, raise_for_status=raise_for_status, **kwargs)

    @override
    def post(self, *args: Any, raise_for_status: bool = True, **kwargs: Any) -> requests.Response:
        return self._request("POST", *args, raise_for_status=raise_for_status, **kwargs)

    @override
    def put(self, *args: Any, raise_for_status: bool = True, **kwargs: Any) -> requests.Response:
        return self._request("PUT", *args, raise_for_status=raise_for_status, **kwargs)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(2),
        reraise=True,
        before_sleep=before_sleep_log(logging.getLogger(), logging.INFO),
    )
    def _request(self, *args: Any, raise_for_status: bool, **kwargs: Any) -> requests.Response:
        timeout = kwargs.pop("timeout", _HTTP_TIMEOUT)

        response = self.request(*args, **kwargs, timeout=timeout)

        if raise_for_status:
            response.raise_for_status()

        return response


http_client = HttpClient()
