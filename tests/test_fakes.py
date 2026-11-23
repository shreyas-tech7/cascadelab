from cascadelab import grader
from cascadelab.fakes import CHEAP, STRONG, FakeProvider
from cascadelab.models import FIXTURES, FixtureStore, record
from cascadelab.tasks import load_visible


def test_cheap_fake_fails_on_its_known_subset():
    """The fixtures' cheap answers are wrong on exactly the tasks the fake marks as failures."""
    tasks = load_visible()
    hidden = grader.load_hidden()
    fake = FakeProvider(0)
    store = FixtureStore(FIXTURES / "fake-seed0")
    known = {tid for tid, t in tasks.items() if not fake.greedy_correct(CHEAP, t)}
    seen = {tid for tid, t in tasks.items() if not grader.correct(t, hidden[tid], store.get("cheap", t).answer)}
    assert known == seen
    assert 30 <= len(known) <= 80


def test_strong_fake_fails_less_often():
    tasks = load_visible().values()
    fake = FakeProvider(0)
    cheap = sum(not fake.greedy_correct(CHEAP, t) for t in tasks)
    strong = sum(not fake.greedy_correct(STRONG, t) for t in tasks)
    assert strong < cheap / 2


def test_committed_fixtures_match_the_fake(tmp_path):
    """Broken case: a hand-edited fixture line no longer matches what the fake records."""
    for seed in (0, 1):
        src = FIXTURES / f"fake-seed{seed}"
        out = tmp_path / src.name
        out.mkdir()
        (out / "manifest.json").write_text((src / "manifest.json").read_text())
        store = FixtureStore(out)
        record(store, FakeProvider(seed), list(load_visible().values()), 5)
        for model in (CHEAP, STRONG):
            assert (out / f"{model}.jsonl").read_bytes() == (src / f"{model}.jsonl").read_bytes()
