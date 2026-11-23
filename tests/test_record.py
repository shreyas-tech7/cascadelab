"""Record mode against a local fake HTTP server. Nothing leaves the machine."""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from cascadelab.models import FixtureStore, OpenAICompatible, record, request_key
from cascadelab.tasks import load_visible


class Handler(BaseHTTPRequestHandler):
    seen: list = []
    fail_first = 0
    fail_code = 429
    content = "42"

    def do_POST(self):  # noqa: N802
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        Handler.seen.append((body, self.headers.get("Authorization")))
        if Handler.fail_first > 0:
            Handler.fail_first -= 1
            self.send_response(Handler.fail_code)
            self.end_headers()
            return
        out = {
            "choices": [{"message": {"content": Handler.content}}],
            "usage": {"prompt_tokens": 30, "completion_tokens": 1},
        }
        data = json.dumps(out).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


@pytest.fixture
def server():
    Handler.seen, Handler.fail_first, Handler.fail_code, Handler.content = [], 0, 429, "42"
    srv = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


def _store(tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps({"cheap": "small-m", "strong": "big-m", "provider": "local"}))
    return FixtureStore(tmp_path)


def test_record_uses_usage_tokens_and_resumes(tmp_path, server, monkeypatch):
    monkeypatch.setenv("TEST_KEY", "sk-test-not-real")
    tasks = list(load_visible().values())[:3]
    prov = OpenAICompatible(server, "TEST_KEY")
    store = _store(tmp_path)
    assert record(store, prov, tasks, k=2, limit=4) == 4
    assert record(_store(tmp_path), prov, tasks, k=2) == 5  # resumes: 3 tasks x 3 calls = 9 in all
    assert record(_store(tmp_path), prov, tasks, k=2) == 0
    final = _store(tmp_path)
    c = final.get("cheap", tasks[0], 1)
    assert c.key == request_key("small-m", tasks[0], 1)
    assert (c.answer, c.prompt_tokens, c.completion_tokens) == ("42", 30, 1)
    assert Handler.seen[0][1] == "Bearer sk-test-not-real"
    assert {b["temperature"] for b, _ in Handler.seen} == {0.0, 0.7}


def test_429_backs_off_and_doubles(server):
    Handler.fail_first = 2
    waits = []
    prov = OpenAICompatible(server, "NO_SUCH_KEY_VAR", sleep=waits.append)
    t = next(iter(load_visible().values()))
    assert prov.complete("m", t, 0)[0] == "42"
    assert waits == [2.0, 4.0]
    assert Handler.seen[0][1] is None


def test_server_errors_back_off_too(server):
    """Broken case: a 503 from the provider ended the whole record run."""
    Handler.fail_first, Handler.fail_code = 1, 503
    waits = []
    prov = OpenAICompatible(server, "NO_SUCH_KEY_VAR", sleep=waits.append)
    assert prov.complete("m", next(iter(load_visible().values())), 0)[0] == "42"
    assert waits == [2.0]


def test_null_content_is_refused(server):
    """Broken case: a response with content null was stored and crashed replay later."""
    Handler.content = None
    prov = OpenAICompatible(server, "NO_SUCH_KEY_VAR", sleep=lambda s: None)
    with pytest.raises(ValueError, match="no text content"):
        prov.complete("m", next(iter(load_visible().values())), 0)


def test_partial_last_line_is_dropped_and_resume_works(tmp_path, server):
    """Broken case: a record run killed mid-write left a partial line, and the next load crashed."""
    tasks = list(load_visible().values())[:2]
    prov = OpenAICompatible(server, "NO_SUCH_KEY_VAR")
    assert record(_store(tmp_path), prov, tasks, k=1) == 4
    path = tmp_path / "small-m.jsonl"
    path.write_text(path.read_text() + '{"key": "abc", "mod')
    store = _store(tmp_path)
    assert len(store.calls) == 4
    assert path.read_text().endswith("}\n")
    assert record(store, prov, tasks, k=1) == 0
