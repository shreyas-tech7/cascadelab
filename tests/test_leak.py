"""The visibility rule: no hidden check, gold answer or hidden test reaches strategy code."""

import ast
import builtins
import dataclasses
import json
import shutil
from pathlib import Path

import pytest

import cascadelab
from cascadelab import evaluate, grader
from cascadelab.models import FIXTURES, FixtureStore
from cascadelab.tasks import DATA, VisibleTask, load_split, load_visible

PKG = Path(cascadelab.__file__).parent
STRATEGY_SIDE = ["strategies.py", "router.py", "checks.py", "models.py", "tasks.py", "costs.py"]
FORBIDDEN = {"grader", "fakes", "taskgen", "evaluate"}
HIDDEN_FILES = {"hidden.jsonl", "world.jsonl"}


def _imports(path: Path) -> set[str]:
    names = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.ImportFrom):
            names.add((node.module or "").split(".")[-1])
            names |= {a.name for a in node.names}
        elif isinstance(node, ast.Import):
            names |= {a.name.split(".")[-1] for a in node.names}
    return names


def test_strategy_side_modules_never_import_hidden_code():
    for name in STRATEGY_SIDE:
        bad = _imports(PKG / name) & FORBIDDEN
        assert not bad, f"{name} imports {bad}"


def test_import_scan_catches_a_leaky_module(tmp_path):
    """Broken case: a strategy file that imports grader is flagged."""
    leaky = tmp_path / "leaky.py"
    leaky.write_text("from . import grader\n")
    assert _imports(leaky) & FORBIDDEN == {"grader"}


def test_visible_task_has_no_hidden_fields():
    fields = {f.name for f in dataclasses.fields(VisibleTask)}
    assert fields == {"id", "family", "prompt", "visible"}
    raw = (DATA / "tasks" / "visible.jsonl").read_text()
    for word in ("gold", "hidden_tests", "hidden"):
        assert f'"{word}"' not in raw


@pytest.fixture
def no_hidden(monkeypatch):
    """Make every route to hidden data raise while strategies run."""

    def boom(*a, **k):
        raise AssertionError("strategy code touched hidden data")

    real_open = builtins.open
    real_read = Path.read_text

    def guarded_open(file, *a, **k):
        if Path(str(file)).name in HIDDEN_FILES:
            boom()
        return real_open(file, *a, **k)

    def guarded_read(self, *a, **k):
        if self.name in HIDDEN_FILES:
            boom()
        return real_read(self, *a, **k)

    monkeypatch.setattr(grader, "load_hidden", boom)
    monkeypatch.setattr(grader, "correct", boom)
    monkeypatch.setattr(builtins, "open", guarded_open)
    monkeypatch.setattr(Path, "read_text", guarded_read)
    return boom


def _setup():
    tasks = load_visible()
    split = load_split()
    store = FixtureStore(FIXTURES / "fake-seed0")
    router = evaluate.train_router(tasks, store, split)
    return [tasks[i] for i in split["heldout"]], store, router


def test_strategies_run_with_hidden_data_locked(no_hidden):
    held, store, router = _SETUP
    out = evaluate.run_strategies(held, store, router)
    assert set(out) == {"cheap_only", "strong_only", "cascade_check", "cascade_agree", "learned_router"}


def test_the_lock_catches_a_leaky_strategy(no_hidden):
    """Broken case: a strategy that peeks at gold answers raises under the lock."""
    with pytest.raises(AssertionError, match="hidden data"):
        grader.load_hidden()
    with pytest.raises(AssertionError, match="hidden data"):
        (DATA / "tasks" / "hidden.jsonl").read_text()


def test_poisoned_hidden_data_changes_no_strategy_output(tmp_path):
    """Replace every gold answer and hidden test with junk. Strategy outputs must not move."""
    held, store, router = _SETUP
    before = evaluate.run_strategies(held, store, router)
    data = tmp_path / "data"
    shutil.copytree(DATA, data)
    rows = [json.loads(x) for x in (data / "tasks" / "hidden.jsonl").read_text().splitlines()]
    junk = [{"id": r["id"], "gold": -999, "hidden_tests": ["assert False"]} for r in rows]
    (data / "tasks" / "hidden.jsonl").write_text("".join(json.dumps(r) + "\n" for r in junk))
    tasks = load_visible(data)
    after = evaluate.run_strategies([tasks[t.id] for t in held], store, router)
    assert before == after


_SETUP = _setup()
