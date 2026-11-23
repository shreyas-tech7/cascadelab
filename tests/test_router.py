"""The router trains on the development split only."""

import json
import shutil

import numpy as np
import pytest

from cascadelab import evaluate
from cascadelab.models import FIXTURES, FixtureStore
from cascadelab.router import Router, hash_embed
from cascadelab.tasks import DATA, load_split, load_visible

STORE = FixtureStore(FIXTURES / "fake-seed0")


def test_fit_refuses_held_out_tasks():
    """Broken case: passing one held-out task to fit raises."""
    tasks, split = load_visible(), load_split()
    dev = [tasks[i] for i in split["dev"][:10]]
    leak = dev + [tasks[split["heldout"][0]]]
    with pytest.raises(ValueError, match="development split only"):
        Router().fit(leak, [False] * len(leak), set(split["dev"]))


def test_trained_router_saw_exactly_the_dev_split():
    split = load_split()
    r = evaluate.train_router(load_visible(), STORE, split)
    assert r.train_ids == sorted(split["dev"])
    assert not set(r.train_ids) & set(split["heldout"])


def _poisoned(tmp_path, ids):
    data = tmp_path / "data"
    shutil.copytree(DATA, data)
    rows = [json.loads(x) for x in (data / "tasks" / "hidden.jsonl").read_text().splitlines()]
    for r in rows:
        if r["id"] in ids:
            r["gold"], r["hidden_tests"] = -999, ["assert False"]
    (data / "tasks" / "hidden.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    return data


def test_held_out_labels_do_not_move_the_router(tmp_path):
    split = load_split()
    base = evaluate.train_router(load_visible(), STORE, split)
    data = _poisoned(tmp_path, set(split["heldout"]))
    again = evaluate.train_router(load_visible(data), STORE, split, data)
    assert np.array_equal(base.w, again.w) and base.b == again.b


def test_dev_labels_do_move_the_router(tmp_path):
    """Sanity check for the test above: the router does react to its training labels."""
    split = load_split()
    base = evaluate.train_router(load_visible(), STORE, split)
    data = _poisoned(tmp_path, set(split["dev"][:20]))
    again = evaluate.train_router(load_visible(data), STORE, split, data)
    assert not np.array_equal(base.w, again.w)


def test_hash_embed_is_stable_and_normalized():
    a, b = hash_embed("sum the numbers"), hash_embed("sum the numbers")
    assert np.array_equal(a, b) and abs(np.linalg.norm(a) - 1) < 1e-12
