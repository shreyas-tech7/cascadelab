"""The learned router: a small text embedding plus logistic regression.

It predicts from the task text alone whether the cheap model will fail. It trains on
development tasks only, and `fit` refuses any task outside the development split.
"""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass, field

import numpy as np

from .tasks import VisibleTask

DIM = 512
WORD = re.compile(r"[a-z_]+|\d+")


def hash_embed(text: str, dim: int = DIM) -> np.ndarray:
    """Signed feature hashing of words and word pairs, L2 normalized. Not learned, fully offline."""
    words = WORD.findall(text.lower())
    vec = np.zeros(dim)
    for tok in words + [a + " " + b for a, b in zip(words, words[1:], strict=False)]:
        h = int.from_bytes(hashlib.blake2b(tok.encode(), digest_size=8).digest(), "little")
        vec[h % dim] += 1.0 if (h >> 63) & 1 else -1.0
    n = np.linalg.norm(vec)
    return vec / n if n else vec


def embedder_name() -> str:
    return "fastembed" if os.environ.get("CASCADELAB_FASTEMBED") == "1" else "hash-512"


def embed(texts: list[str]) -> np.ndarray:
    if embedder_name() == "fastembed":  # pragma: no cover - needs the model download
        from fastembed import TextEmbedding

        return np.array(list(TextEmbedding("BAAI/bge-small-en-v1.5").embed(texts)))
    return np.array([hash_embed(t) for t in texts])


@dataclass
class Router:
    threshold: float = 0.5
    l2: float = 1.0
    w: np.ndarray | None = None
    b: float = 0.0
    train_ids: list[str] = field(default_factory=list)
    embedder: str = ""

    def fit(self, tasks: list[VisibleTask], cheap_failed: list[bool], dev_ids: set[str]) -> Router:
        """Fit on development tasks. Labels say whether the cheap answer failed the hidden check."""
        outside = [t.id for t in tasks if t.id not in dev_ids]
        if outside:
            raise ValueError(f"router may train on the development split only, got {outside[:3]}")
        x = embed([t.prompt for t in tasks])
        y = np.array(cheap_failed, dtype=float)
        # Balanced class weights, so a 0.5 threshold means "more likely to fail than not".
        pos = max(y.sum(), 1.0)
        neg = max(len(y) - y.sum(), 1.0)
        sw = np.where(y == 1, len(y) / (2 * pos), len(y) / (2 * neg))
        w, b = np.zeros(x.shape[1]), 0.0
        for _ in range(800):
            p = 1 / (1 + np.exp(-(x @ w + b)))
            g = sw * (p - y)
            w -= 0.5 * (x.T @ g / len(y) + self.l2 * w / len(y))
            b -= 0.5 * g.mean()
        self.w, self.b = w, float(b)
        self.train_ids = sorted(t.id for t in tasks)
        self.embedder = embedder_name()
        return self

    def p_fail(self, task: VisibleTask) -> float:
        z = float(embed([task.prompt])[0] @ self.w + self.b)
        return round(1 / (1 + np.exp(-z)), 12)

    def escalate(self, task: VisibleTask) -> bool:
        return self.p_fail(task) >= self.threshold
