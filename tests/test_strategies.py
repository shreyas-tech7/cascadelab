import json

import numpy as np

from cascadelab.checks import normalize, visible_check
from cascadelab.models import FIXTURES, Call, FixtureStore, request_key
from cascadelab.router import Router
from cascadelab.strategies import cascade_agree, cascade_check, cheap_only, make_routed, strong_only
from cascadelab.tasks import VisibleTask, load_visible

T = VisibleTask("math-x", "math", "What is 2 + 2?", {"kind": "number", "steps": 1})


def _store(tmp_path, cheap: list[str], strong: str) -> FixtureStore:
    (tmp_path / "manifest.json").write_text(json.dumps({"cheap": "c", "strong": "s", "provider": "test"}))
    store = FixtureStore(tmp_path)
    for i, a in enumerate(cheap):
        store.add(Call(request_key("c", T, i), "c", i, a, 10, 2, 100 + i))
    store.add(Call(request_key("s", T, 0), "s", 0, strong, 10, 2, 500))
    return store


def test_cascade_check_escalates_only_on_visible_failure(tmp_path):
    store = _store(tmp_path, ["no idea", "4", "4", "4", "4"], "4")
    o = cascade_check(T, store)
    assert o.escalated and o.answer == "4" and o.latency_ms == 600 and len(o.calls) == 2
    (tmp_path / "b").mkdir()
    o2 = cascade_check(T, _store(tmp_path / "b", ["5"] * 5, "4"))
    assert not o2.escalated and o2.answer == "5"


def test_cascade_agree(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    agree = cascade_agree(T, _store(tmp_path / "a", ["4", "4.0", "$4", "4", "4"], "9"))
    assert not agree.escalated and agree.answer == "4" and agree.latency_ms == 104
    split = cascade_agree(T, _store(tmp_path / "b", ["4", "4", "5", "4", "4"], "9"))
    assert split.escalated and split.answer == "9" and split.latency_ms == 104 + 500


def test_router_strategy_follows_the_router(tmp_path):
    store = _store(tmp_path, ["5"] * 5, "4")
    always, never = Router(threshold=0.0), Router(threshold=1.1)
    always.w = never.w = np.zeros(512)
    assert make_routed(always)(T, store).answer == "4"
    assert make_routed(never)(T, store).answer == "5"


def test_strategies_on_real_fixtures_follow_their_rules():
    store = FixtureStore(FIXTURES / "fake-seed0")
    for t in list(load_visible().values())[::7]:
        c, s = store.get("cheap", t), store.get("strong", t)
        assert cheap_only(t, store).answer == c.answer and strong_only(t, store).answer == s.answer
        assert cascade_check(t, store).escalated == (not visible_check(t, c.answer))
        keys = {normalize(t, store.get("cheap", t, i).answer) for i in range(5)}
        assert cascade_agree(t, store).escalated == (len(keys) > 1)


def test_agreement_on_unparseable_answers_escalates(tmp_path):
    """Broken case: five different unparseable answers all normalize to "none" and count as agreement."""
    out = cascade_agree(T, _store(tmp_path, ["no idea", "unsure", "?", "pass", "n/a"], "4"))
    assert out.escalated and out.answer == "4"
