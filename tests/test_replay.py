"""Every strategy runs end to end from fixtures and gives byte-identical results twice."""

from cascadelab.cli import main
from cascadelab.evaluate import ORDER


def test_run_twice_is_byte_identical(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    assert main(["run", "--fixtures", "fake-seed0", "--out", str(a)]) == 0
    assert main(["run", "--fixtures", "fake-seed0", "--out", str(b)]) == 0
    for name in ("fake-seed0.json", "fake-seed0-tasks.jsonl"):
        assert (a / name).read_bytes() == (b / name).read_bytes()


def test_every_strategy_has_results_on_both_splits(tmp_path):
    import json

    main(["run", "--fixtures", "fake-seed0", "--out", str(tmp_path)])
    r = json.loads((tmp_path / "fake-seed0.json").read_text())
    for split, n in (("heldout", 72), ("dev", 108)):
        assert set(r["splits"][split]) == set(ORDER)
        for s in ORDER:
            assert r["splits"][split][s]["n"] == n


def test_committed_results_match_a_fresh_replay(tmp_path):
    """Broken case: a hand-edited number in results/ no longer matches the replay."""
    from cascadelab.cli import RESULTS

    main(["run", "--out", str(tmp_path)])
    for name in ("fake-seed0.json", "fake-seed1.json"):
        assert (tmp_path / name).read_bytes() == (RESULTS / name).read_bytes()
