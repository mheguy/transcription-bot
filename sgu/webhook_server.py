import http.server
import socketserver
from inspect import isawaitable
from queue import Queue
from threading import Thread

import ngrok

from sgu.config import NGROK_TOKEN, SERVER_PORT
from sgu.custom_logger import logger


class WebhookServer:
    def __init__(self) -> None:
        self._queue = Queue(1)
        self._server_thread = Thread(target=self._start_server, daemon=False)
        self._listener: ngrok.Listener | None = None

    async def start_server_thread(self) -> str:
        self._server_thread.start()
        listener = ngrok.forward(SERVER_PORT, authtoken=NGROK_TOKEN)  # BUG: An _asyncio.Task is being returned here

        if isawaitable(listener):
            listener = await listener

        self._listener = listener
        return listener.url()

    async def get_webhook_payload_async(self) -> bytes:
        if self._listener is None:
            raise RuntimeError("Server not started")

        self._server_thread.join()
        self._listener.close()
        return self._queue.get()

    def create_handler_class(self) -> type[http.server.SimpleHTTPRequestHandler]:
        server_instance = self

        class CustomHandler(http.server.SimpleHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802
                logger.info("Got callback...")

                content_length = int(self.headers["Content-Length"])
                post_data = self.rfile.read(content_length)

                server_instance._queue.put(post_data)  # noqa: SLF001

                self.send_response(200)
                self.end_headers()

        return CustomHandler

    def _start_server(self) -> None:
        handler_class = self.create_handler_class()
        with socketserver.TCPServer(("", SERVER_PORT), handler_class) as httpd:
            logger.info("Serving on port %s", SERVER_PORT)
            httpd.handle_request()
            logger.info("Server has shut down")
