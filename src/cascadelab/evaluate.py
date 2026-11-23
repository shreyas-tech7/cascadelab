"""The replay harness: train the router, run every strategy, score with hidden checks, aggregate.

Order matters for the visibility rule. Strategies run first and see visible tasks only.
Scoring with hidden checks happens after, in a separate step. The oracle lives here, not
in strategies.py, because it reads hidden results. It is an upper bound, never a claim.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import grader
from .costs import call_cost, load_prices
from .metrics import paired_bootstrap, percentile, unpaired_bootstrap, wilson
from .models import FixtureStore
from .router import Router
from .strategies import STATIC, K, Outcome, make_routed
from .tasks import DATA, VisibleTask, load_split, load_visible

ORDER = ["cheap_only", "strong_only", "cascade_check", "cascade_agree", "learned_router", "oracle_router"]
LABELS = {
    "cheap_only": "Cheap model only",
    "strong_only": "Strong model only",
    "cascade_check": "Cascade on visible check",
    "cascade_agree": f"Cascade on agreement (k={K})",
    "learned_router": "Learned router",
    "oracle_router": "Oracle router (upper bound)",
}


def train_router(tasks: dict[str, VisibleTask], store: FixtureStore, split: dict, data_dir: Path = DATA) -> Router:
    """Labels come from hidden checks on the development split only."""
    hidden = grader.load_hidden(data_dir)
    dev = [tasks[i] for i in split["dev"]]
    failed = [not grader.correct(t, hidden[t.id], store.get("cheap", t).answer) for t in dev]
    return Router().fit(dev, failed, set(split["dev"]))


def run_strategies(tasks: list[VisibleTask], store: FixtureStore, router: Router) -> dict[str, list[Outcome]]:
    """Run every non-oracle strategy. Takes visible tasks only and reads no hidden data."""
    fns = dict(STATIC) | {"learned_router": make_routed(router)}
    return {name: [fn(t, store) for t in tasks] for name, fn in fns.items()}


def _r(x: float) -> float:
    return round(x, 6)


def _summary(name, tasks, outcomes, right, strong_right, costs, strong_costs) -> dict:
    n, k = len(tasks), sum(right)
    lo, hi = wilson(k, n)
    lat = [o.latency_ms for o in outcomes]
    d, dlo, dhi = paired_bootstrap(right, strong_right)
    cd, cdlo, cdhi = paired_bootstrap(costs, strong_costs)
    fam = {}
    for f in ("math", "json", "code"):
        idx = [i for i, t in enumerate(tasks) if t.family == f]
        fam[f] = _r(sum(right[i] for i in idx) / len(idx)) if idx else None
    return {
        "label": LABELS[name],
        "n": n,
        "correct": k,
        "accuracy": _r(k / n),
        "accuracy_ci95": [_r(lo), _r(hi)],
        "cost_per_1000_usd": _r(1000 * sum(costs) / n),
        "latency_p50_ms": _r(percentile(lat, 50)),
        "latency_p95_ms": _r(percentile(lat, 95)),
        "escalation_rate": _r(sum(o.escalated for o in outcomes) / n),
        "calls_per_task": _r(sum(len(o.calls) for o in outcomes) / n),
        "vs_strong_accuracy": [_r(d), _r(dlo), _r(dhi)],
        "vs_strong_cost_per_1000_usd": [_r(1000 * cd), _r(1000 * cdlo), _r(1000 * cdhi)],
        "accuracy_by_family": fam,
    }


def evaluate_split(tasks, store, router, hidden, prices) -> tuple[dict, list[dict]]:
    outcomes = run_strategies(tasks, store, router)
    right = {
        name: [grader.correct(t, hidden[t.id], o.answer) for t, o in zip(tasks, outs, strict=True)]
        for name, outs in outcomes.items()
    }
    # Oracle: knows from the hidden check whether the cheap answer is right, and calls only the model it needs.
    outcomes["oracle_router"] = [
        o_c if ok else o_s
        for o_c, o_s, ok in zip(outcomes["cheap_only"], outcomes["strong_only"], right["cheap_only"], strict=True)
    ]
    outcomes["oracle_router"] = [
        Outcome(o.answer, o.calls, not ok, o.latency_ms)
        for o, ok in zip(outcomes["oracle_router"], right["cheap_only"], strict=True)
    ]
    right["oracle_router"] = [a or b for a, b in zip(right["cheap_only"], right["strong_only"], strict=True)]
    costs = {name: [sum(call_cost(c, prices) for c in o.calls) for o in outs] for name, outs in outcomes.items()}
    out = {
        name: _summary(
            name, tasks, outcomes[name], right[name], right["strong_only"], costs[name], costs["strong_only"]
        )
        for name in ORDER
    }
    rows = [
        {
            "task": t.id,
            "strategy": name,
            "correct": right[name][i],
            "escalated": outcomes[name][i].escalated,
            "calls": len(outcomes[name][i].calls),
            "tokens": sum(c.prompt_tokens + c.completion_tokens for c in outcomes[name][i].calls),
            "cost_usd": _r(costs[name][i]),
            "latency_ms": outcomes[name][i].latency_ms,
        }
        for name in ORDER
        for i, t in enumerate(tasks)
    ]
    return out, rows


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(fixture_dir: Path, data_dir: Path = DATA) -> tuple[dict, list[dict]]:
    tasks = load_visible(data_dir)
    split = load_split(data_dir)
    store = FixtureStore(fixture_dir)
    prices = load_prices(data_dir)
    router = train_router(tasks, store, split, data_dir)
    hidden = grader.load_hidden(data_dir)
    result = {
        "fixtures": fixture_dir.name,
        "manifest": store.manifest,
        "prices_checked_on": prices["checked_on"],
        "priced_as": {m: prices["models"][m]["priced_as"] for m in store.models.values()},
        "agreement_k": K,
        "bootstrap": {"reps": 2000, "seed": 0},
        "router": {"embedder": router.embedder, "threshold": router.threshold, "train_ids": router.train_ids},
        "task_files_sha256": {
            n: file_sha(data_dir / "tasks" / n) for n in ("visible.jsonl", "hidden.jsonl", "split.json")
        },
        "splits": {},
    }
    all_rows = []
    for name in ("heldout", "dev"):
        ts = [tasks[i] for i in split[name]]
        summary, rows = evaluate_split(ts, store, router, hidden, prices)
        result["splits"][name] = summary
        all_rows += [r | {"split": name} for r in rows]
    s = result["splits"]["heldout"]
    a = [r["correct"] for r in all_rows if r["split"] == "heldout" and r["strategy"] == "cascade_check"]
    b = [r["correct"] for r in all_rows if r["split"] == "heldout" and r["strategy"] == "strong_only"]
    lo, hi = unpaired_bootstrap(a, b)
    s["cascade_check"]["vs_strong_accuracy_unpaired_ci95"] = [_r(lo), _r(hi)]
    return result, all_rows


def write(result: dict, rows: list[dict], out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    main = out_dir / f"{result['fixtures']}.json"
    per = out_dir / f"{result['fixtures']}-tasks.jsonl"
    main.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    per.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows), encoding="utf-8")
    return main, per
