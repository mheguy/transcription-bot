import http.server
import socketserver
from inspect import isawaitable
from queue import Queue
from threading import Thread

import ngrok
from loguru import logger

from transcription_bot.utils.config import config


class WebhookServer:
    """Provide a temporary server that accepts a webhook call.

    Pyannote.ai returns results via webhook.
    This server fits that need by using ngrok to create a temporary public URL
    and then listening for a single request to that URL.
    """

    def __init__(self) -> None:
        self._queue: Queue[bytes] = Queue(1)
        self._server_thread = Thread(target=self._start_server, daemon=False)
        self._listener: ngrok.Listener | None = None

    def start_server_thread(self) -> str:
        """Start the server in a separate thread and return the public URL of the server."""
        self._server_thread.start()
        listener = ngrok.forward(config.server_port, authtoken=config.ngrok_token)

        if isawaitable(listener):
            raise TypeError("Listener is awaitable")

        self._listener = listener
        return listener.url()

    def stop_server_thread(self) -> None:
        """Stop the server thread."""
        if self._listener is not None:
            self._listener.close()
            self._listener = None

    def get_webhook_payload(self) -> bytes:
        """Get the webhook payload."""
        if self._listener is None:
            raise RuntimeError("Server not started")

        self._server_thread.join()
        return self._queue.get()

    def _create_handler_class(self) -> type[http.server.SimpleHTTPRequestHandler]:
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
        handler_class = self._create_handler_class()
        with socketserver.TCPServer(("", config.server_port), handler_class) as httpd:
            logger.info(f"Serving on port {config.server_port}")
            httpd.handle_request()
            logger.info("Server has shut down")
