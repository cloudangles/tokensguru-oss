"""The local web server for `tokensguru docs`.

It uses only Python's standard library. It serves the pages in tokensguru/ui and a
few internal JSON endpoints that the docs pages use to run the optimizers on your own
machine. They are not a public API and are not documented for outside use.

Safety: it listens on 127.0.0.1 only, answers only requests addressed to
localhost, refuses requests from other websites, limits the request size, never
reads files outside the ui folder, and sends strict security headers.

    GET  /api/health       {"status": "ok", "version": "..."}
    GET  /api/optimizers   what the UI shows about each optimizer
    GET  /api/benchmark    token savings of one optimizer on its sample inputs
    POST /api/optimize     {"optimizer": "<id>", "text": "..."}  (or "messages")
    GET  /api/guardrails   what the UI shows about each guardrail
    GET  /api/guardrail-benchmark   detection accuracy of one guardrail
    POST /api/check        {"guardrail": "<id>", "text": "..."}  (or "messages")
"""

from __future__ import annotations

import hashlib
import json
import threading
import webbrowser
from collections.abc import Callable
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from tokensguru.server.catalog import (
    RequestError,
    benchmark_for,
    describe_optimizers,
    run_optimization,
)
from tokensguru.server.guardrail_catalog import (
    describe_guardrails,
    guardrail_benchmark_for,
    run_check,
)
from tokensguru.version import __version__

DEFAULT_PORT = 8765
LOCAL_HOSTS = ("127.0.0.1", "localhost", "::1")
MAX_BODY_BYTES = 2_000_000
UI_DIR = Path(__file__).resolve().parent.parent / "ui"

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
    ".webp": "image/webp",
    ".txt": "text/plain; charset=utf-8",
}
SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; "
        "base-uri 'none'; form-action 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
}


def _hostname(host_header: str) -> str:
    host = host_header.strip().lower()
    if host.startswith("["):
        return host[1 : host.find("]")] if "]" in host else host
    return host.rsplit(":", 1)[0] if host.count(":") == 1 else host


class DocsHandler(BaseHTTPRequestHandler):
    server_version = "tokensguru"
    sys_version = ""
    protocol_version = "HTTP/1.1"
    timeout = 30
    wbufsize = -1
    disable_nagle_algorithm = True

    def log_message(self, format: str, *args: object) -> None:
        del format, args

    def do_GET(self) -> None:
        self._handle(send_body=True)

    def do_HEAD(self) -> None:
        self._handle(send_body=False)

    def do_POST(self) -> None:
        if not self._request_is_local():
            return
        routes = {"/api/optimize": run_optimization, "/api/check": run_check}
        route = routes.get(urlsplit(self.path).path)
        if route is None:
            self._send_error(HTTPStatus.NOT_FOUND, "Not found.")
            return
        try:
            self._send_json(route(self._read_json()))
        except RequestError as error:
            self._send_error(error.status, error.message)
        except Exception:
            self._send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "Internal error.")

    def _method_not_allowed(self) -> None:
        self._send_error(HTTPStatus.METHOD_NOT_ALLOWED, "Method not allowed.")

    do_PUT = do_DELETE = do_PATCH = _method_not_allowed

    def _handle(self, *, send_body: bool) -> None:
        if not self._request_is_local():
            return
        path = urlsplit(self.path).path
        if path == "/api/health":
            self._send_json({"status": "ok", "version": __version__}, send_body)
        elif path == "/api/optimizers":
            self._send_json(describe_optimizers(), send_body)
        elif path == "/api/guardrails":
            self._send_json(describe_guardrails(), send_body)
        elif path == "/api/guardrail-benchmark":
            self._send_guardrail_benchmark(urlsplit(self.path).query, send_body)
        elif path == "/api/benchmark":
            self._send_benchmark(urlsplit(self.path).query, send_body)
        elif path.startswith("/api/"):
            self._send_error(HTTPStatus.NOT_FOUND, "Not found.")
        else:
            self._send_file(path, send_body)

    def _send_benchmark(self, query: str, send_body: bool) -> None:
        identifier = parse_qs(query).get("optimizer", [""])[0]
        try:
            self._send_json(benchmark_for(identifier), send_body)
        except RequestError as error:
            self._send_error(error.status, error.message)

    def _send_guardrail_benchmark(self, query: str, send_body: bool) -> None:
        identifier = parse_qs(query).get("guardrail", [""])[0]
        try:
            self._send_json(guardrail_benchmark_for(identifier), send_body)
        except RequestError as error:
            self._send_error(error.status, error.message)

    def _request_is_local(self) -> bool:
        host = self.headers.get("Host", "")
        origin = self.headers.get("Origin")
        if _hostname(host) not in LOCAL_HOSTS:
            self._send_error(HTTPStatus.FORBIDDEN, "Only localhost is allowed.")
            return False
        if origin is not None and urlsplit(origin).netloc.lower() != host.lower():
            self._send_error(HTTPStatus.FORBIDDEN, "Cross-origin requests are refused.")
            return False
        return True

    def _read_json(self) -> object:
        if not self.headers.get("Content-Type", "").startswith("application/json"):
            raise RequestError(415, "Send the request as application/json.")
        length = self.headers.get("Content-Length")
        if length is None or not length.isdigit():
            raise RequestError(411, "A Content-Length header is required.")
        if int(length) > MAX_BODY_BYTES:
            raise RequestError(
                413, f"The request is larger than {MAX_BODY_BYTES} bytes."
            )
        try:
            return json.loads(self.rfile.read(int(length)).decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as error:
            raise RequestError(400, "The request body is not valid JSON.") from error

    def _send_file(self, url_path: str, send_body: bool) -> None:
        target = _resolve_static(url_path)
        if target is None:
            self._send_error(HTTPStatus.NOT_FOUND, "Not found.")
            return
        data = target.read_bytes()
        if target == UI_DIR / "index.html":
            data = _with_module_preloads(data)
        tag = f'"{hashlib.sha1(data).hexdigest()[:16]}"'  # noqa: S324
        if self.headers.get("If-None-Match") == tag:
            self._send(HTTPStatus.NOT_MODIFIED, b"", "", False, etag=tag)
            return
        content_type = CONTENT_TYPES.get(
            target.suffix.lower(), "application/octet-stream"
        )
        self._send(HTTPStatus.OK, data, content_type, send_body, etag=tag)

    def _send_json(self, data: object, send_body: bool = True) -> None:
        body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self._send(HTTPStatus.OK, body, "application/json; charset=utf-8", send_body)

    def _send_error(self, status: int, message: str) -> None:
        self.close_connection = True
        body = json.dumps({"error": message}).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8", True)

    def _send(
        self,
        status: int,
        body: bytes,
        content_type: str,
        send_body: bool,
        *,
        etag: str | None = None,
    ) -> None:
        self.send_response(status)
        if content_type:
            self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache" if etag else "no-store")
        if etag:
            self.send_header("ETag", etag)
        if self.close_connection:
            self.send_header("Connection", "close")
        for name, value in SECURITY_HEADERS.items():
            self.send_header(name, value)
        self.end_headers()
        if send_body:
            self.wfile.write(body)


def _with_module_preloads(page: bytes) -> bytes:
    scripts = sorted((UI_DIR / "js").rglob("*.js"))
    links = "\n    ".join(
        f'<link rel="modulepreload" href="{script.relative_to(UI_DIR).as_posix()}" />'
        for script in scripts
    )
    return page.replace(b"<!--modulepreload-->", links.encode("utf-8"))


def _resolve_static(url_path: str) -> Path | None:
    relative = unquote(url_path).lstrip("/")
    parts = relative.split("/") if relative else []
    if any(part == ".." or "\\" in part or "\x00" in part for part in parts):
        return None
    target = (UI_DIR / relative).resolve() if relative else UI_DIR.resolve()
    ui_root = UI_DIR.resolve()
    if target != ui_root and ui_root not in target.parents:
        return None
    if target.is_dir():
        target = target / "index.html"
    return target if target.is_file() else None


def make_server(host: str = "127.0.0.1", port: int = 0) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), DocsHandler)
    server.daemon_threads = True
    return server


def _bind(port: int | None) -> ThreadingHTTPServer:
    if port is not None:
        return make_server(port=port)
    try:
        return make_server(port=DEFAULT_PORT)
    except OSError:
        return make_server(port=0)


def _say(message: str) -> None:
    print(message, flush=True)


def serve(
    port: int | None = None,
    open_browser: bool = True,
    opener: Callable[[str], object] = webbrowser.open,
    announce: Callable[[str], object] = _say,
) -> int:
    server = _bind(port)
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    announce(f"tokensguru docs is running at {url}")
    announce("Press Ctrl+C to stop.")
    if open_browser:
        threading.Thread(target=opener, args=(url,), daemon=True).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        announce("Stopped.")
    finally:
        server.server_close()
    return 0
