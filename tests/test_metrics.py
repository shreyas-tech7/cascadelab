import numpy as np

from cascadelab.costs import call_cost, load_prices
from cascadelab.metrics import paired_bootstrap, percentile, unpaired_bootstrap, wilson
from cascadelab.models import Call


def test_wilson_known_value():
    lo, hi = wilson(8, 10)
    assert abs(lo - 0.4902) < 1e-3 and abs(hi - 0.9433) < 1e-3
    assert wilson(0, 0) == (0.0, 0.0)


def test_paired_is_tighter_when_scores_move_together():
    rng = np.random.default_rng(1)
    base = (rng.random(200) < 0.8).astype(float)
    a = base.copy()
    a[rng.choice(200, 6, replace=False)] = 0
    d, lo, hi = paired_bootstrap(a, base)
    ulo, uhi = unpaired_bootstrap(a, base)
    assert lo <= d <= hi
    assert (hi - lo) < (uhi - ulo) / 2


def test_percentile_and_cost():
    assert percentile([1, 2, 3, 4], 50) == 2.5
    prices = load_prices()
    c = Call("k", "fake-strong", 0, "x", 1_000_000, 1_000_000, 1)
    assert abs(call_cost(c, prices) - (0.59 + 0.79)) < 1e-12
