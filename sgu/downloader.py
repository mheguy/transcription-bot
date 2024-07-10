from httpx import AsyncClient, Client
from requests import Session


class Mp3Downloader:
    def __init__(self, client: "AsyncClient | Client | Session") -> None:
        self.client = client

    async def download_async(self, url: str) -> bytes:
        if not isinstance(self.client, AsyncClient):
            raise TypeError("client provided was sync, you cannot use this method")

        response = await self.client.get(url)
        response.raise_for_status()

        return response.content

    def download(self, url: str) -> bytes:
        if not isinstance(self.client, Client | Session):
            raise TypeError("client provided was async, you cannot use this method")

        response = self.client.get(url)
        response.raise_for_status()

        return response.content
