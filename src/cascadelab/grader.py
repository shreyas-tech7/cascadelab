"""Hidden checks: gold answers and hidden tests. Scoring only.

Strategy code must never import this module. `tests/test_leak.py` enforces that.
"""

from __future__ import annotations

import json
from pathlib import Path

from .checks import parse_json, parse_number, run_tests, strip_fence
from .tasks import DATA, VisibleTask


def load_hidden(data_dir: Path = DATA) -> dict[str, dict]:
    rows = (data_dir / "tasks" / "hidden.jsonl").read_text(encoding="utf-8").splitlines()
    return {r["id"]: r for r in map(json.loads, rows)}


def _same(a, b) -> bool:
    if isinstance(b, bool) or isinstance(a, bool):
        return a is b
    if isinstance(b, (int, float)) and isinstance(a, (int, float)):
        return abs(a - b) < 1e-9
    if isinstance(b, list) and isinstance(a, list):
        return len(a) == len(b) and all(_same(x, y) for x, y in zip(a, b, strict=True))
    if isinstance(b, str) and isinstance(a, str):
        return a.strip() == b.strip()
    return False


def correct(task: VisibleTask, hidden: dict, answer: str) -> bool:
    kind = task.visible["kind"]
    if kind == "number":
        n = parse_number(answer)
        return n is not None and abs(n - hidden["gold"]) < 1e-9
    if kind == "json":
        obj = parse_json(answer)
        gold = hidden["gold"]
        return obj is not None and set(obj) == set(gold) and all(_same(obj[k], gold[k]) for k in gold)
    code = strip_fence(answer)
    return run_tests(code, tuple(task.visible["example_tests"])) and run_tests(code, tuple(hidden["hidden_tests"]))
