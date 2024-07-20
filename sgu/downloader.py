from httpx import AsyncClient, Client
from requests import Session


class FileDownloader:
    """A light wrapper to provide both sync and async downloads."""

    def __init__(self, client: "AsyncClient | Client | Session") -> None:
        self.client = client

    async def download_async(self, url: str) -> bytes:
        """Asynchronously download a file from the given URL."""
        if not isinstance(self.client, AsyncClient):
            raise TypeError("client provided was sync, you must call `get`")

        response = await self.client.get(url)
        response.raise_for_status()

        return response.content

    def download(self, url: str) -> bytes:
        """Download a file from the given URL."""
        if not isinstance(self.client, Client | Session):
            raise TypeError("client provided was async, you must call `get_async`")

        response = self.client.get(url)
        response.raise_for_status()

        return response.content
