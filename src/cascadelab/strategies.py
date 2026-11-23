"""The strategies. Each one sees a VisibleTask and the fixture store, and nothing else.

A strategy returns its final answer and the calls it made. It may run visible checks only.
This module must never import `grader`, `fakes` or `taskgen`. `tests/test_leak.py` checks it.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .checks import normalize, visible_check
from .models import Call, FixtureStore
from .router import Router
from .tasks import VisibleTask

K = 5  # cheap samples for the agreement cascade


@dataclass(frozen=True)
class Outcome:
    answer: str
    calls: tuple[Call, ...]
    escalated: bool
    latency_ms: int


def _one(call: Call, escalated: bool = False) -> Outcome:
    return Outcome(call.answer, (call,), escalated, call.latency_ms)


def cheap_only(task: VisibleTask, store: FixtureStore) -> Outcome:
    return _one(store.get("cheap", task))


def strong_only(task: VisibleTask, store: FixtureStore) -> Outcome:
    return _one(store.get("strong", task))


def cascade_check(task: VisibleTask, store: FixtureStore) -> Outcome:
    """Keep the cheap answer if it passes the visible check, else ask the strong model."""
    cheap = store.get("cheap", task)
    if visible_check(task, cheap.answer):
        return _one(cheap)
    strong = store.get("strong", task)
    return Outcome(strong.answer, (cheap, strong), True, cheap.latency_ms + strong.latency_ms)


def cascade_agree(task: VisibleTask, store: FixtureStore, k: int = K) -> Outcome:
    """Sample k cheap answers in parallel. Keep the first one if all k agree and parse, else ask the strong model."""
    samples = [store.get("cheap", task, s) for s in range(k)]
    wait = max(c.latency_ms for c in samples)
    keys = {normalize(task, c.answer) for c in samples}
    if len(keys) == 1 and "none" not in keys:
        return Outcome(samples[0].answer, tuple(samples), False, wait)
    strong = store.get("strong", task)
    return Outcome(strong.answer, (*samples, strong), True, wait + strong.latency_ms)


def make_routed(router: Router) -> Callable[[VisibleTask, FixtureStore], Outcome]:
    def routed(task: VisibleTask, store: FixtureStore) -> Outcome:
        """Ask the router first. Send the task straight to the strong model if it predicts a cheap failure."""
        return _one(store.get("strong", task), True) if router.escalate(task) else _one(store.get("cheap", task))

    return routed


STATIC = {
    "cheap_only": cheap_only,
    "strong_only": strong_only,
    "cascade_check": cascade_check,
    "cascade_agree": cascade_agree,
}
