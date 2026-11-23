"""Answer parsing, visible checks and the subprocess test runner.

Visible checks use only what a real system has at run time: the answer format, the JSON
schema and the example tests printed in the task text. Hidden scoring reuses the parsers
and the runner, but lives in `grader.py`.
"""

from __future__ import annotations

import functools
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from .tasks import VisibleTask

NUMBER = re.compile(r"^\$?\s*(-?\d+(?:\.\d+)?)\s*$")
FENCE = re.compile(r"^```[a-zA-Z]*\n(.*?)\n?```$", re.S)
TYPES = {
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "array": lambda v: isinstance(v, list),
}
TEST_TIMEOUT_S = 5


def strip_fence(text: str) -> str:
    text = text.strip()
    m = FENCE.match(text)
    return m.group(1).strip() if m else text


def parse_number(text: str) -> float | None:
    m = NUMBER.match(strip_fence(text).replace(",", ""))
    return float(m.group(1)) if m else None


def parse_json(text: str):
    try:
        obj = json.loads(strip_fence(text))
    except ValueError:
        return None
    return obj if isinstance(obj, dict) else None


def schema_ok(obj, schema: dict) -> bool:
    return isinstance(obj, dict) and set(obj) == set(schema) and all(TYPES[t](obj[k]) for k, t in schema.items())


def _limits() -> None:  # pragma: no cover - runs in the child process
    import resource

    resource.setrlimit(resource.RLIMIT_CPU, (TEST_TIMEOUT_S, TEST_TIMEOUT_S))
    resource.setrlimit(resource.RLIMIT_AS, (512 * 2**20, 512 * 2**20))


@functools.lru_cache(maxsize=8192)
def run_tests(code: str, tests: tuple[str, ...]) -> bool:
    """Run code plus assert lines in a fresh Python subprocess in a temp folder. True if all pass.

    shortcut: a subprocess with a timeout, CPU and memory limits is not a full sandbox. Run only
    model code you are willing to execute on this machine.
    """
    src = code + "\n\n" + "\n".join(tests) + "\n"
    with tempfile.TemporaryDirectory(prefix="cascadelab-") as tmp:
        path = Path(tmp) / f"t_{hashlib.sha256(src.encode()).hexdigest()[:12]}.py"
        path.write_text(src, encoding="utf-8")
        try:
            proc = subprocess.run(  # noqa: S603 - fixed interpreter, file we just wrote
                [sys.executable, "-I", "-S", str(path)],
                cwd=tmp,
                env={"PATH": os.environ.get("PATH", "")},
                capture_output=True,
                timeout=TEST_TIMEOUT_S,
                preexec_fn=_limits if os.name == "posix" else None,  # noqa: PLW1509
            )
        except subprocess.TimeoutExpired:
            return False
    return proc.returncode == 0


def visible_check(task: VisibleTask, answer: str) -> bool:
    """The check a real system can run at run time, with no access to gold answers."""
    v = task.visible
    if v["kind"] == "number":
        return parse_number(answer) is not None
    if v["kind"] == "json":
        return schema_ok(parse_json(answer), v["schema"])
    return run_tests(strip_fence(answer), tuple(v["example_tests"]))


def normalize(task: VisibleTask, answer: str) -> str:
    """Key used to decide whether two answers agree."""
    kind = task.visible["kind"]
    if kind == "number":
        n = parse_number(answer)
        return "none" if n is None else repr(n)
    if kind == "json":
        obj = parse_json(answer)
        return "none" if obj is None else json.dumps(obj, sort_keys=True)
    return "\n".join(line.rstrip() for line in strip_fence(answer).splitlines() if line.strip())
