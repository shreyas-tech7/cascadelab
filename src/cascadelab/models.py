"""Model calls through a fixture cache.

Every call is keyed by a hash of (model, messages, temperature, sample). Replay reads the
fixture files only and never touches the network. Record mode fills missing keys from a
provider, appends them, and resumes where it stopped.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

from .tasks import VisibleTask

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "fixtures"


@dataclass(frozen=True)
class Call:
    key: str
    model: str
    sample: int
    answer: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int


class MissingFixture(KeyError):
    pass


def temperature(sample: int) -> float:
    return 0.0 if sample == 0 else 0.7


def request_key(model: str, task: VisibleTask, sample: int) -> str:
    body = {"model": model, "messages": task.messages(), "temperature": temperature(sample), "sample": sample}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


class FixtureStore:
    """Fixture folder: manifest.json names the models, then one JSONL file per model."""

    def __init__(self, folder: Path):
        self.folder = Path(folder)
        self.manifest = json.loads((self.folder / "manifest.json").read_text(encoding="utf-8"))
        self.models = {"cheap": self.manifest["cheap"], "strong": self.manifest["strong"]}
        self.calls: dict[str, Call] = {}
        for model in self.models.values():
            path = self.folder / f"{model}.jsonl"
            if path.exists():
                lines = path.read_text(encoding="utf-8").splitlines()
                for i, line in enumerate(lines):
                    try:
                        c = Call(**json.loads(line))
                    except (json.JSONDecodeError, TypeError):
                        if i == len(lines) - 1:
                            # A record run stopped mid-write. Drop the partial line so the next append
                            # starts clean. Record again fills this call.
                            path.write_text("".join(x + "\n" for x in lines[:-1]), encoding="utf-8")
                            break
                        raise
                    self.calls[c.key] = c

    def get(self, role: str, task: VisibleTask, sample: int = 0) -> Call:
        key = request_key(self.models[role], task, sample)
        if key not in self.calls:
            raise MissingFixture(f"no fixture for {role} {task.id} sample {sample} in {self.folder}")
        return self.calls[key]

    def add(self, call: Call) -> None:
        self.calls[call.key] = call
        with (self.folder / f"{call.model}.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(call), sort_keys=True) + "\n")

    def tidy(self) -> None:
        """Rewrite each model file sorted by key, so the files diff cleanly."""
        for model in self.models.values():
            rows = sorted((c for c in self.calls.values() if c.model == model), key=lambda c: c.key)
            text = "".join(json.dumps(asdict(c), sort_keys=True) + "\n" for c in rows)
            (self.folder / f"{model}.jsonl").write_text(text, encoding="utf-8")


def plan(tasks: list[VisibleTask], k: int) -> list[tuple[str, VisibleTask, int]]:
    """Every request the strategies need: k cheap samples and one strong answer per task."""
    return [(role, t, s) for t in tasks for role, s in [("cheap", i) for i in range(k)] + [("strong", 0)]]


def record(store: FixtureStore, provider, tasks: list[VisibleTask], k: int, limit: int | None = None) -> int:
    """Fill missing fixtures. Returns how many new calls were made. Safe to rerun: it resumes."""
    made = 0
    for role, task, sample in plan(tasks, k):
        model = store.models[role]
        key = request_key(model, task, sample)
        if key in store.calls:
            continue
        if limit is not None and made >= limit:
            break
        answer, pt, ct, ms = provider.complete(model, task, sample)
        store.add(Call(key, model, sample, answer, pt, ct, ms))
        made += 1
    store.tidy()
    return made


class OpenAICompatible:
    """A chat completions endpoint (Groq, OpenRouter). Reads the key from an environment variable."""

    PROVIDERS = {
        "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY"),
        "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
    }

    def __init__(self, base_url: str, key_env: str, timeout_s: float = 60, sleep=time.sleep):
        self.base_url, self.key_env, self.timeout_s, self.sleep = base_url.rstrip("/"), key_env, timeout_s, sleep

    @classmethod
    def named(cls, name: str) -> OpenAICompatible:
        return cls(*cls.PROVIDERS[name])

    def complete(self, model: str, task: VisibleTask, sample: int) -> tuple[str, int, int, int]:
        body = {"model": model, "messages": task.messages(), "temperature": temperature(sample), "seed": sample}
        headers = {"Content-Type": "application/json"}
        key = os.environ.get(self.key_env)
        if key:
            headers["Authorization"] = f"Bearer {key}"
        wait = 2.0
        for attempt in range(5):
            req = urllib.request.Request(  # noqa: S310 - base URL is a fixed https provider or a local test server
                f"{self.base_url}/chat/completions", data=json.dumps(body).encode(), headers=headers
            )
            start = time.perf_counter()
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:  # noqa: S310
                    data = json.loads(resp.read())
            except urllib.error.HTTPError as e:
                if (e.code == 429 or e.code >= 500) and attempt < 4:
                    self.sleep(wait)
                    wait *= 2
                    continue
                raise
            except urllib.error.URLError:
                if attempt < 4:
                    self.sleep(wait)
                    wait *= 2
                    continue
                raise
            ms = round((time.perf_counter() - start) * 1000)
            usage = data["usage"]
            content = data["choices"][0]["message"]["content"]
            if not isinstance(content, str):
                raise ValueError(f"{model} returned no text content")
            return content, usage["prompt_tokens"], usage["completion_tokens"], ms
        raise RuntimeError("unreachable")
