import logging
from dataclasses import dataclass
from typing import Any, override

import requests
import tls_client
from loguru import logger
from tenacity import before_sleep_log, retry, stop_after_attempt, wait_fixed
from tls_client.exceptions import TLSClientExeption

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
        try:
            return self._request("GET", *args, raise_for_status=raise_for_status, **kwargs)
        except Exception:
            if resp := get_with_evasion(*args, raise_for_status=raise_for_status, **kwargs):
                return resp

            raise

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

        if raise_for_status and not response.ok:
            logger.exception(f"Request failed: {response}")
            response.raise_for_status()

        return response


def get_with_evasion(*args: Any, raise_for_status: bool, **kwargs: Any) -> requests.Response | None:
    """Get a webpage while simulating a browser."""
    try:
        resp = tls_client.Session().execute_request("GET", *args, **kwargs)
    except TLSClientExeption:
        return None

    requests_resp = requests.Response()
    requests_resp.status_code = resp.status_code or 400

    if raise_for_status and not requests_resp.ok:
        return None

    if not isinstance(resp.content, bytes):
        return None

    requests_resp.raw = MockRawResponse(resp.content)

    return requests_resp


http_client = HttpClient()
