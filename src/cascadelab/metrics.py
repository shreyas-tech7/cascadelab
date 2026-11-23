"""Accuracy intervals, paired bootstrap differences and latency percentiles."""

from __future__ import annotations

import math

import numpy as np


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    p = k / n
    d = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, mid - half), min(1.0, mid + half)


def paired_bootstrap(a: list[float], b: list[float], reps: int = 2000, seed: int = 0) -> tuple[float, float, float]:
    """Mean of a - b over the same tasks, with a 95% percentile interval from resampling tasks."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = a - b
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(d), size=(reps, len(d)))
    means = d[idx].mean(axis=1)
    lo, hi = np.percentile(means, [2.5, 97.5])
    return float(d.mean()), float(lo), float(hi)


def unpaired_bootstrap(a: list[float], b: list[float], reps: int = 2000, seed: int = 0) -> tuple[float, float]:
    """Same difference with tasks resampled separately for a and b. Shown only to compare widths."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    rng = np.random.default_rng(seed)
    ma = a[rng.integers(0, len(a), size=(reps, len(a)))].mean(axis=1)
    mb = b[rng.integers(0, len(b), size=(reps, len(b)))].mean(axis=1)
    lo, hi = np.percentile(ma - mb, [2.5, 97.5])
    return float(lo), float(hi)


def percentile(values: list[float], q: float) -> float:
    return float(np.percentile(np.asarray(values, float), q))
