import logging
from dataclasses import dataclass
from typing import Any, override

import requests
import tls_client
from tenacity import before_sleep_log, retry, stop_after_attempt, wait_fixed

__all__ = ["http_client"]

_CUSTOM_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0"}
_HTTP_TIMEOUT = 15


@dataclass
class MockRawResponse:
    content: bytes | None

    def read(self, _) -> bytes | None:
        if content := self.content:
            self.content = None
            return content

        return None


class HttpClient(requests.Session):
    def __init__(self):
        super().__init__()
        self.headers.update(_CUSTOM_HEADERS)

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


def get_with_evasion(url: str) -> requests.Response:
    """Get a webpage while simulating a browser."""
    resp = tls_client.Session().execute_request("GET", url)

    requests_resp = requests.Response()
    requests_resp.status_code = resp.status_code or 400

    if isinstance(resp.content, bytes):
        requests_resp.raw = MockRawResponse(resp.content)
    else:
        requests_resp.raw = MockRawResponse(None)

    return requests_resp


http_client = HttpClient()
