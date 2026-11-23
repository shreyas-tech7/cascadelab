"""The fake model pair: a cheap fake and a strong fake.

They stand in for real models when no provider key exists. Each fake answers from
data/fake/world.jsonl (one correct answer and several wrong ones per task). Whether a
fake gets a task right is a fixed function of (seed, model, task), so the cheap fake
fails on a known subset. Harder tasks (more steps, more fields, harder functions) fail
more often. Some wrong answers fail the visible check and some only fail the hidden one.
Strategy code never imports this module.
"""

from __future__ import annotations

import json
import math
import random
from pathlib import Path

from .tasks import DATA, VisibleTask

CHEAP, STRONG = "fake-cheap", "fake-strong"
# Share of wrong answers that a visible check can catch, by model and family.
VISIBLE_SHARE = {CHEAP: {"math": 0.2, "json": 0.55, "code": 0.5}, STRONG: {"math": 0.05, "json": 0.3, "code": 0.3}}


def cheap_fail_rate(task: VisibleTask) -> float:
    v = task.visible
    if v["kind"] == "number":
        return 0.08 + 0.09 * v["steps"]
    if v["kind"] == "json":
        return 0.04 + 0.05 * (len(v["schema"]) - 4) + 0.08 * v["distractors"]
    return 0.12 + 0.13 * v["level"]


def fail_rate(model: str, task: VisibleTask) -> float:
    p = cheap_fail_rate(task)
    return p if model == CHEAP else 0.25 * p + 0.01


class FakeProvider:
    def __init__(self, seed: int = 0, data_dir: Path = DATA):
        self.seed = seed
        rows = (data_dir / "fake" / "world.jsonl").read_text(encoding="utf-8").splitlines()
        self.world = {r["id"]: r for r in map(json.loads, rows)}

    def greedy_correct(self, model: str, task: VisibleTask) -> bool:
        return random.Random(f"{self.seed}|{model}|{task.id}|greedy").random() >= fail_rate(model, task)  # noqa: S311 - seeded fake, not security

    def _wrong(self, model: str, task: VisibleTask, rng: random.Random) -> str:
        w = self.world[task.id]
        pool = w["visible_fail"] if rng.random() < VISIBLE_SHARE[model][task.family] else w["hidden_fail"]
        return rng.choice(pool)

    def answer(self, model: str, task: VisibleTask, sample: int) -> str:
        rng = random.Random(f"{self.seed}|{model}|{task.id}|{sample}")  # noqa: S311 - seeded fake, not security
        good = self.greedy_correct(model, task)
        if sample > 0:
            good = rng.random() < (0.85 if good else 0.35)
        return self.world[task.id]["correct"][0] if good else self._wrong(model, task, rng)

    def complete(self, model: str, task: VisibleTask, sample: int) -> tuple[str, int, int, int]:
        text = self.answer(model, task, sample)
        pt = math.ceil(sum(len(m["content"]) for m in task.messages()) / 4)
        ct = math.ceil(len(text) / 4) + 2
        jitter = random.Random(f"{self.seed}|{model}|{task.id}|{sample}|ms").random()  # noqa: S311 - seeded fake, not security
        ms = 120 + 4 * ct + 60 * jitter if model == CHEAP else 380 + 15 * ct + 200 * jitter
        return text, pt, ct, round(ms)
