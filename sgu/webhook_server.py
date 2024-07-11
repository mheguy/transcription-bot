import http.server
import os
import socketserver
from queue import Queue
from threading import Thread
from typing import Any

import ngrok

from sgu.config import SERVER_PORT

NGROK_TOKEN = os.environ["NGROK_TOKEN"]


class WebhookServer:
    def __init__(self) -> None:
        self._queue = Queue(1)
        self._server_thread = Thread(target=self._start_server, daemon=True)
        self._listener: ngrok.Listener | None = None

    def start_server_thread(self) -> str:
        self._server_thread.start()
        listener = ngrok.forward(SERVER_PORT, authtoken=NGROK_TOKEN)
        self._listener = listener
        return listener.url()

    def get_webhook_payload(self) -> dict[str, Any]:
        if self._listener is None:
            raise RuntimeError("Server not started")

        self._server_thread.join()
        self._listener.close()
        return self._queue.get()

    def create_handler_class(self) -> type[http.server.SimpleHTTPRequestHandler]:
        server_instance = self

        class CustomHandler(http.server.SimpleHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802
                print("Got callback...")

                content_length = int(self.headers["Content-Length"])
                post_data = self.rfile.read(content_length).decode("utf-8")

                server_instance._queue.put(post_data)  # noqa: SLF001

                self.send_response(200)
                self.end_headers()

        return CustomHandler

    def _start_server(self) -> None:
        handler_class = self.create_handler_class()
        with socketserver.TCPServer(("", SERVER_PORT), handler_class) as httpd:
            print(f"Serving on port {SERVER_PORT}")
            httpd.handle_request()
            print("Server has shut down")


if __name__ == "__main__":
    server = WebhookServer()
    url = server.start_server_thread()
    print(f"Listening on {url}")
    print("Do lots of things in the main thread...")
    print("Waiting for payload to be sent to webhook...")
    payload = server.get_webhook_payload()
    print(f"Received payload: {payload}")
