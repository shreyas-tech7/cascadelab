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

    def do_POST(self):  # noqa: N802
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        Handler.seen.append((body, self.headers.get("Authorization")))
        if Handler.fail_first > 0:
            Handler.fail_first -= 1
            self.send_response(429)
            self.end_headers()
            return
        out = {"choices": [{"message": {"content": "42"}}], "usage": {"prompt_tokens": 30, "completion_tokens": 1}}
        data = json.dumps(out).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


@pytest.fixture
def server():
    Handler.seen, Handler.fail_first = [], 0
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
