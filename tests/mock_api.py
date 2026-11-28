"""A local mock of the GitHub, OSV and deps.dev APIs for the HTTP tests.

    with MockAPI() as api:
        api.route("GET", "/repos/o/r", [(429, {"Retry-After": "1"}, None), (200, {}, {"ok": True})])
        common.http_json("GET", api.url + "/repos/o/r")

Routes match the method and the path without its query string. Each route returns its responses in order and
repeats the last one. An unrouted path returns 404 {"message": "Not Found"}. Every request is recorded in
.requests as (method, full path with query, headers, parsed JSON body or None).
"""
import json
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

NOT_FOUND = (404, {}, {"message": "Not Found"})


class MockAPI:
    def __init__(self):
        self._routes = {}
        self.requests = []
        self._lock = threading.Lock()
        self._server = None
        self._thread = None

    def route(self, method, path, responses):
        """Queue (status, headers, body) responses for method + path; the last one repeats."""
        with self._lock:
            self._routes[(method.upper(), path)] = [(s, dict(h), b) for s, h, b in responses]

    @property
    def url(self):
        if self._server is None:
            raise RuntimeError("MockAPI is not running")
        host, port = self._server.server_address[:2]
        return f"http://{host}:{port}"

    def _next(self, method, full_path, headers, body):
        """Record the request and return the response for it, under the lock."""
        path = urllib.parse.urlsplit(full_path).path
        with self._lock:
            self.requests.append((method, full_path, headers, body))
            queue = self._routes.get((method, path))
            if not queue:
                return NOT_FOUND
            status, hdrs, resp = queue[0] if len(queue) == 1 else queue.pop(0)
            return status, dict(hdrs), resp

    def __enter__(self):
        api = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):  # keep test output quiet
                pass

            def _handle(self):
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b""
                try:
                    body = json.loads(raw) if raw else None
                except ValueError:
                    body = None
                status, headers, resp = api._next(self.command, self.path, dict(self.headers.items()), body)
                data = b"" if resp is None else json.dumps(resp).encode()
                self.send_response(status)
                if resp is not None:
                    headers.setdefault("Content-Type", "application/json")
                headers["Content-Length"] = str(len(data))
                for name, value in headers.items():
                    self.send_header(name, value)
                self.end_headers()
                self.wfile.write(data)

            do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = _handle

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._server.shutdown()
        self._server.server_close()
        self._thread.join()
        self._server = None
