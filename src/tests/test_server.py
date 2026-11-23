import http.client
import json
import threading
from pathlib import Path

import pytest

from tokensguru import __version__
from tokensguru.optimizers.registry import MESSAGE_OPTIMIZERS, TEXT_OPTIMIZERS
from tokensguru.server import app as server_app
from tokensguru.server import catalog, make_server, serve
from tokensguru.server.catalog import RequestError, describe_optimizers

JSON = {"Content-Type": "application/json"}


@pytest.fixture
def server():
    httpd = make_server()
    thread = threading.Thread(
        target=lambda: httpd.serve_forever(poll_interval=0.01), daemon=True
    )
    thread.start()
    yield httpd.server_address[1]
    httpd.shutdown()
    httpd.server_close()
    thread.join(timeout=5)


def call(port, method, path, body=None, headers=None, *, host=None):  # noqa: PLR0913
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    all_headers = dict(headers or {})
    connection.putrequest(method, path, skip_host=host is not None)
    if host is not None:
        connection.putheader("Host", host)
    for name, value in all_headers.items():
        connection.putheader(name, value)
    if body is not None:
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        connection.putheader("Content-Length", str(len(data)))
        connection.endheaders(data)
    else:
        connection.endheaders()
    response = connection.getresponse()
    payload = response.read()
    connection.close()
    return response.status, dict(response.getheaders()), payload


def post(port, payload, **kwargs):
    headers = kwargs.pop("headers", JSON)
    status, _, body = call(port, "POST", "/api/optimize", payload, headers, **kwargs)
    return status, json.loads(body) if body else None


def test_serves_the_index_page(server):
    status, headers, body = call(server, "GET", "/")
    assert status == 200
    assert headers["Content-Type"] == "text/html; charset=utf-8"
    assert body.startswith(b"<!doctype html>")


def test_head_returns_headers_without_a_body(server):
    status, headers, body = call(server, "HEAD", "/")
    assert status == 200
    assert body == b""
    assert int(headers["Content-Length"]) > 0


def test_health(server):
    status, _, body = call(server, "GET", "/api/health")
    assert status == 200
    assert json.loads(body) == {"status": "ok", "version": __version__}


def test_security_headers_are_sent(server):
    _, headers, _ = call(server, "GET", "/")
    assert "default-src 'self'" in headers["Content-Security-Policy"]
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["Referrer-Policy"] == "no-referrer"
    assert headers["X-Frame-Options"] == "DENY"
    _, headers, _ = call(server, "GET", "/api/health")
    assert headers["Cache-Control"] == "no-store"


def test_unknown_pages_and_api_paths_are_404(server):
    assert call(server, "GET", "/nope.html")[0] == 404
    assert call(server, "GET", "/api/nope")[0] == 404
    assert call(server, "POST", "/api/other", {}, JSON)[0] == 404


@pytest.mark.parametrize(
    "path",
    [
        "/../pyproject.toml",
        "/%2e%2e/%2e%2e/pyproject.toml",
        "/..%2f..%2fpyproject.toml",
        "/js/../../version.py",
        "/..\\..\\version.py",
        "/%00",
        "//etc/passwd",
        "/../../../../../../etc/passwd",
    ],
)
def test_cannot_read_files_outside_the_ui_folder(server, path):
    status, _, body = call(server, "GET", path)
    assert status in (403, 404)
    assert b"__version__" not in body
    assert b"root:" not in body


def test_other_http_methods_are_refused(server):
    for method in ("PUT", "DELETE", "PATCH"):
        assert call(server, method, "/", b"{}")[0] == 405


def test_lists_every_optimizer(server):
    status, _, body = call(server, "GET", "/api/optimizers")
    entries = json.loads(body)
    assert status == 200
    ids = [entry["id"] for entry in entries]
    assert ids[0] == "pipeline"
    assert ids[1:] == [o.id for o in TEXT_OPTIMIZERS] + [
        o.id for o in MESSAGE_OPTIMIZERS
    ]
    for entry in entries:
        assert entry["name"]
        assert entry["summary"]
        assert entry["description"]
        assert entry["kind"] in ("pipeline", "text", "messages")
        assert entry["example"]


def test_every_registered_optimizer_has_a_working_example():
    for entry in describe_optimizers():
        key = "messages" if entry["kind"] == "messages" else "text"
        result = catalog.run_optimization(
            {"optimizer": entry["id"], key: entry["example"]}
        )
        assert result["changed"] is True, entry["id"]


def test_runs_a_text_optimizer(server):
    status, result = post(
        server, {"optimizer": "prose_whitespace_cleanup", "text": "a    b  \n"}
    )
    assert status == 200
    assert result["optimized_text"] == "a b\n"
    assert result["optimizer_id"] == "prose_whitespace_cleanup"
    assert result["original_tokens"] is not None
    assert result["saved_tokens"] is not None
    assert result["id"]


def test_runs_the_pipeline_with_steps(server):
    status, result = post(server, {"optimizer": "pipeline", "text": "a    b  \n"})
    assert status == 200
    assert result["optimized_text"] == "a b\n"
    assert result["steps"][0]["optimizer_id"] == "tokenguru_json_minifier"


def test_runs_the_message_optimizer(server):
    message = {"role": "system", "content": "A"}
    status, result = post(
        server,
        {"optimizer": "exact_duplicate_system_messages", "messages": [message] * 2},
    )
    assert status == 200
    assert result["optimized_messages"] == [message]
    assert result["removed_indexes"] == [1]


def test_unicode_round_trip(server):
    text = "café    \U0001f600"
    _, result = post(server, {"optimizer": "prose_whitespace_cleanup", "text": text})
    assert result["optimized_text"] == "café \U0001f600"


@pytest.mark.parametrize(
    ("payload", "status"),
    [
        ({"optimizer": "nope", "text": "a"}, 404),
        ({"text": "a"}, 400),
        ({"optimizer": 5, "text": "a"}, 400),
        ({"optimizer": "pipeline"}, 400),
        ({"optimizer": "pipeline", "text": 5}, 400),
        ({"optimizer": "prose_whitespace_cleanup", "text": ["a"]}, 400),
        ({"optimizer": "exact_duplicate_system_messages"}, 400),
        ({"optimizer": "exact_duplicate_system_messages", "messages": "x"}, 400),
        ([1, 2], 400),
        ("text", 400),
    ],
)
def test_bad_requests_get_a_clear_error(server, payload, status):
    code, result = post(server, payload)
    assert code == status
    assert result["error"]


def test_invalid_json_is_a_400(server):
    code, _, body = call(server, "POST", "/api/optimize", b"{not json", JSON)
    assert code == 400
    assert "error" in json.loads(body)
    code, _, _ = call(server, "POST", "/api/optimize", b"\xff\xfe", JSON)
    assert code == 400


def test_post_must_be_json(server):
    headers = {"Content-Type": "text/plain"}
    code, _, _ = call(server, "POST", "/api/optimize", b"{}", headers)
    assert code == 415
    code, _, _ = call(server, "POST", "/api/optimize", b"{}", {})
    assert code == 415


def test_post_needs_a_content_length(server):
    code, _, _ = call(server, "POST", "/api/optimize", None, JSON)
    assert code == 411


def test_oversized_requests_are_refused(server, monkeypatch):
    monkeypatch.setattr(server_app, "MAX_BODY_BYTES", 100)
    code, _, _ = call(server, "POST", "/api/optimize", b" " * 200, JSON)
    assert code == 413


def test_a_request_from_another_site_is_refused(server):
    headers = {**JSON, "Origin": "http://evil.example"}
    code, _, _ = call(server, "POST", "/api/optimize", {"optimizer": "x"}, headers)
    assert code == 403
    code, _, _ = call(
        server, "GET", "/api/health", None, {"Origin": "http://evil.example"}
    )
    assert code == 403


def test_a_request_from_the_same_origin_is_allowed(server):
    headers = {**JSON, "Origin": f"http://127.0.0.1:{server}"}
    body = {"optimizer": "prose_whitespace_cleanup", "text": "a  b"}
    assert call(server, "POST", "/api/optimize", body, headers)[0] == 200


@pytest.mark.parametrize(
    "host", ["evil.example", "evil.example:80", "10.0.0.5:8765", ""]
)
def test_a_request_for_another_host_is_refused(server, host):
    assert call(server, "GET", "/api/health", host=host)[0] == 403


@pytest.mark.parametrize(
    "host", ["localhost", "LOCALHOST:1234", "[::1]:1234", "127.0.0.1"]
)
def test_localhost_names_are_accepted(server, host):
    assert call(server, "GET", "/api/health", host=host)[0] == 200


def test_unexpected_errors_do_not_leak_details(server, monkeypatch):
    def boom(payload):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(server_app, "run_optimization", boom)
    code, result = post(server, {"optimizer": "pipeline", "text": "a"})
    assert code == 500
    assert "secret" not in json.dumps(result)


def test_hostname_helper():
    assert server_app._hostname("localhost:8000") == "localhost"
    assert server_app._hostname("[::1]:8000") == "::1"
    assert server_app._hostname("[::1") == "[::1"
    assert server_app._hostname("127.0.0.1") == "127.0.0.1"


def test_resolve_static_only_returns_files_inside_the_ui_folder():
    assert server_app._resolve_static("/") == server_app.UI_DIR / "index.html"
    assert server_app._resolve_static("/index.html").name == "index.html"
    assert server_app._resolve_static("/missing") is None
    assert server_app._resolve_static("/../server/app.py") is None
    assert server_app.UI_DIR.name == "ui"
    assert Path(server_app.__file__).parent.name == "server"


def test_request_error_carries_status_and_message():
    error = RequestError(418, "teapot")
    assert (error.status, error.message) == (418, "teapot")


def test_serve_opens_the_browser_and_stops_on_ctrl_c(monkeypatch):
    opened, said = [], []
    monkeypatch.setattr(
        server_app.ThreadingHTTPServer,
        "serve_forever",
        lambda self: (_ for _ in ()).throw(KeyboardInterrupt()),
    )
    assert serve(port=0, opener=opened.append, announce=said.append) == 0
    for _ in range(100):
        if opened:
            break
        threading.Event().wait(0.05)
    assert opened and opened[0].startswith("http://127.0.0.1:")
    assert any("is running at" in line for line in said)
    assert said[-1] == "Stopped."


def test_serve_does_not_open_the_browser_when_told_not_to(monkeypatch):
    opened = []
    monkeypatch.setattr(
        server_app.ThreadingHTTPServer,
        "serve_forever",
        lambda self: (_ for _ in ()).throw(KeyboardInterrupt()),
    )
    serve(port=0, open_browser=False, opener=opened.append, announce=lambda _: None)
    threading.Event().wait(0.2)
    assert opened == []


def test_the_default_port_is_used_then_a_free_port_if_it_is_busy():
    first = server_app._bind(None)
    try:
        second = server_app._bind(None)
        try:
            assert second.server_address[1] != first.server_address[1]
        finally:
            second.server_close()
    finally:
        first.server_close()


def test_an_explicit_busy_port_is_an_error():
    first = make_server()
    try:
        with pytest.raises(OSError):
            server_app._bind(first.server_address[1])
    finally:
        first.server_close()


def test_messages_are_flushed_so_they_show_when_output_is_piped(capsys, monkeypatch):
    flushed = []
    real_print = print

    def spy(*args, **kwargs):
        flushed.append(kwargs.get("flush"))
        real_print(*args, **kwargs)

    monkeypatch.setattr("builtins.print", spy)
    server_app._say("hello")
    assert flushed == [True]
    assert "hello" in capsys.readouterr().out


def test_benchmark_endpoint(server):
    status, _, body = call(
        server, "GET", "/api/benchmark?optimizer=exact_bullet_item_deduplication"
    )
    report = json.loads(body)
    assert status == 200
    assert report["optimizer"] == "exact_bullet_item_deduplication"
    assert report["error"] is None
    assert report["summary"]["samples"] >= 5
    assert report["samples"][0]["name"]
    assert report["tokenizer"]


def test_benchmark_endpoint_serves_every_optimizer(server, whitespace_tokens):
    for entry in describe_optimizers():
        status, _, body = call(server, "GET", f"/api/benchmark?optimizer={entry['id']}")
        assert status == 200, entry["id"]
        assert json.loads(body)["summary"]["average_percent"] > 0


@pytest.mark.parametrize(
    "query", ["", "?optimizer=", "?optimizer=nope", "?other=pipeline"]
)
def test_benchmark_endpoint_rejects_unknown_optimizers(server, query):
    status, _, body = call(server, "GET", f"/api/benchmark{query}")
    assert status == 404
    assert "error" in json.loads(body)


def test_benchmark_results_are_cached(server, monkeypatch):
    calls = []
    real = catalog.run_benchmark

    def counting(identifier, counter=None):
        calls.append(identifier)
        return real(identifier, counter)

    catalog._BENCHMARKS.clear()
    monkeypatch.setattr(catalog, "run_benchmark", counting)
    for _ in range(3):
        assert call(server, "GET", "/api/benchmark?optimizer=pipeline")[0] == 200
    assert calls == ["pipeline"]


def test_a_failed_benchmark_is_not_cached(monkeypatch):
    catalog._BENCHMARKS.clear()
    monkeypatch.setattr(
        catalog,
        "run_benchmark",
        lambda identifier, counter=None: {
            "optimizer": identifier,
            "error": "offline",
            "samples": [],
            "summary": None,
        },
    )
    assert catalog.benchmark_for("pipeline")["error"] == "offline"
    assert "pipeline" not in catalog._BENCHMARKS


def test_static_files_have_an_etag_and_return_304_when_unchanged(server):
    _, headers, body = call(server, "GET", "/assets/styles.css")
    tag = headers["ETag"]
    assert tag.startswith('"') and body
    assert headers["Cache-Control"] == "no-cache"
    status, headers_304, body_304 = call(
        server, "GET", "/assets/styles.css", headers={"If-None-Match": tag}
    )
    assert status == 304
    assert body_304 == b""
    assert headers_304["ETag"] == tag
    assert "Content-Security-Policy" in headers_304


def test_a_different_etag_gets_the_full_file(server):
    status, _, body = call(
        server, "GET", "/assets/styles.css", headers={"If-None-Match": '"stale"'}
    )
    assert status == 200
    assert body


def test_etag_differs_per_file(server):
    tags = {
        call(server, "GET", path)[1]["ETag"]
        for path in ("/assets/styles.css", "/js/app.js", "/js/dom.js")
    }
    assert len(tags) == 3


def test_the_index_page_preloads_every_module(server):
    _, _, body = call(server, "GET", "/")
    page = body.decode()
    assert "<!--modulepreload-->" not in page
    scripts = sorted((server_app.UI_DIR / "js").rglob("*.js"))
    assert len(scripts) > 20
    for script in scripts:
        relative = script.relative_to(server_app.UI_DIR).as_posix()
        assert f'<link rel="modulepreload" href="{relative}" />' in page
    assert page.count("modulepreload") == len(scripts)


def test_the_index_page_loads_the_theme_before_the_page_paints(server):
    page = call(server, "GET", "/")[2].decode()
    assert page.index("js/theme-init.js") < page.index('type="module"')
    assert 'name="color-scheme"' in page


def test_one_connection_can_serve_many_requests(server):
    connection = http.client.HTTPConnection("127.0.0.1", server, timeout=10)
    try:
        for path in ("/", "/assets/styles.css", "/js/app.js", "/api/health"):
            connection.request("GET", path)
            response = connection.getresponse()
            assert response.status == 200, path
            assert response.read()
            assert response.getheader("Connection") != "close", path
    finally:
        connection.close()


def test_a_keep_alive_connection_can_mix_gets_and_posts(server):
    connection = http.client.HTTPConnection("127.0.0.1", server, timeout=10)
    try:
        body = json.dumps({"optimizer": "prose_whitespace_cleanup", "text": "a  b"})
        connection.request("POST", "/api/optimize", body, JSON)
        first = connection.getresponse()
        assert json.loads(first.read())["optimized_text"] == "a b"
        connection.request("GET", "/api/health")
        assert connection.getresponse().status == 200
    finally:
        connection.close()


def test_an_error_closes_the_connection_so_an_unread_body_cannot_leak(server):
    connection = http.client.HTTPConnection("127.0.0.1", server, timeout=10)
    try:
        connection.request(
            "POST", "/api/optimize", b"x" * 50, {"Content-Type": "text/plain"}
        )
        response = connection.getresponse()
        response.read()
        assert response.status == 415
        assert response.getheader("Connection") == "close"
    finally:
        connection.close()


def test_the_png_logo_is_served_and_the_heavy_svg_is_gone(server):
    status, headers, body = call(server, "GET", "/assets/logo-mark.png")
    assert (status, headers["Content-Type"]) == (200, "image/png")
    assert len(body) < 30_000
    assert call(server, "GET", "/assets/tokensguru-logo.svg")[0] == 404
    assert (
        server_app.UI_DIR / "assets" / "tokensguru-wordmark.png"
    ).stat().st_size < 30_000
