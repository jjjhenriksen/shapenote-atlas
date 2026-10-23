"""Synthetic, loopback-only responses for the native WebKit regression."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


PAYLOAD = bytes(range(256)) * 256
PAGE = b"""<!doctype html><title>Native download fixture</title>
<a id="action" href="/score.bin" download="fixture.musicxml">Download</a>
<a id="response" href="/score.bin">Response download</a>
<a id="broken" href="/broken.bin" download>Broken download</a>
"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = PAGE if self.path == "/" else PAYLOAD
        self.send_response(200)
        self.send_header("Content-Type", "text/html" if self.path == "/" else "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.path == "/broken.bin":
            self.wfile.write(body[:16])
            self.wfile.flush()
            self.close_connection = True
        else:
            self.wfile.write(body)

    def log_message(self, *_):
        pass


server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
print(server.server_port, flush=True)
server.serve_forever()
