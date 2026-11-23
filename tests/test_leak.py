"""The visibility rule: no hidden check, gold answer or hidden test reaches strategy code."""

import ast
import dataclasses
import io
import os
import subprocess
import sys
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


_LOCKED = False


def _audit(event, args):
    """Python audit hook. While the lock is on, block every route to hidden files.

    The "open" event fires for builtins.open, io.open, os.open, Path.read_text, Path.read_bytes
    and Path.open alike, so a strategy cannot get round the lock by picking another file API.
    Subprocesses are blocked too, except the test runner in checks.run_tests.
    """
    if not _LOCKED:
        return
    if event == "open":
        target = args[0]
        if isinstance(target, (str, bytes, Path)) and Path(os.fsdecode(target)).name in HIDDEN_FILES:
            raise AssertionError(f"strategy code touched hidden data: {target}")
    elif event == "subprocess.Popen":
        exe, argv = args[0], list(args[1] or [])
        runner = os.fsdecode(exe or "") == sys.executable and argv[1:3] == ["-I", "-S"]
        if not (runner and len(argv) == 4 and "cascadelab-" in str(argv[3])):
            raise AssertionError(f"strategy code started a process: {argv}")
    elif event in {"os.system", "os.exec", "os.posix_spawn", "os.spawn"}:
        raise AssertionError(f"strategy code started a process: {event}")


sys.addaudithook(_audit)


@pytest.fixture
def no_hidden(monkeypatch):
    """Make every route to hidden data raise while strategies run."""
    global _LOCKED

    def boom(*a, **k):
        raise AssertionError("strategy code touched hidden data")

    monkeypatch.setattr(grader, "load_hidden", boom)
    monkeypatch.setattr(grader, "correct", boom)
    _LOCKED = True
    try:
        yield
    finally:
        _LOCKED = False


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
    assert all(len(v) == len(held) for v in out.values())


HIDDEN = DATA / "tasks" / "hidden.jsonl"
LEAKS = {
    "read_text": lambda: HIDDEN.read_text(),
    "read_bytes": lambda: HIDDEN.read_bytes(),
    "path_open": lambda: HIDDEN.open("rb").close(),
    "builtin_open": lambda: open(HIDDEN, "rb").close(),  # noqa: SIM115
    "io_open": lambda: io.open(HIDDEN, "rb").close(),  # noqa: SIM115, UP020
    "os_open": lambda: os.close(os.open(HIDDEN, os.O_RDONLY)),
    "relative_path": lambda: open(os.path.relpath(HIDDEN), "rb").close(),  # noqa: SIM115
    "world_file": lambda: (DATA / "fake" / "world.jsonl").read_bytes(),
    "grader": lambda: grader.load_hidden(),
    "subprocess": lambda: subprocess.run(["cat", str(HIDDEN)], capture_output=True, check=False),  # noqa: S603, S607
}


@pytest.mark.parametrize("route", sorted(LEAKS))
def test_the_lock_catches_a_leaky_strategy(no_hidden, monkeypatch, route):
    """Broken case: a strategy that peeks at hidden data by any file API raises inside run_strategies."""
    held, store, router = _SETUP

    def leaky(task, store_):
        LEAKS[route]()
        return evaluate.STATIC["cheap_only"](task, store_)

    monkeypatch.setattr(evaluate, "STATIC", dict(evaluate.STATIC) | {"leaky": leaky})
    with pytest.raises(AssertionError, match="hidden data|started a process"):
        evaluate.run_strategies(held[:1], store, router)


_SETUP = _setup()


def test_only_the_harness_imports_the_grader():
    """Broken case: report.py or cli.py imports grader and starts scoring outside the harness."""
    users = {p.name for p in PKG.glob("*.py") if "grader" in _imports(p) and p.name != "grader.py"}
    assert users == {"evaluate.py"}
