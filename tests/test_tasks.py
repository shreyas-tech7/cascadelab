import json
from collections import Counter

from cascadelab import grader, taskgen
from cascadelab.checks import visible_check
from cascadelab.tasks import DATA, load_split, load_visible


def test_counts_and_split():
    tasks = load_visible()
    assert Counter(t.family for t in tasks.values()) == {"math": 60, "json": 60, "code": 60}
    split = load_split()
    assert len(split["dev"]) == 108 and len(split["heldout"]) == 72
    assert not set(split["dev"]) & set(split["heldout"])
    assert set(split["dev"]) | set(split["heldout"]) == set(tasks)
    for fam in ("math", "json", "code"):
        assert sum(i.startswith(fam) for i in split["heldout"]) == 24


def test_task_files_are_frozen():
    """Broken case: editing a task file or the generator changes a hash and fails here."""
    want = json.loads((DATA / "FROZEN.json").read_text())
    for rel, text in taskgen.render().items():
        assert taskgen.sha(text) == want[rel], rel
        assert (DATA / rel).read_text(encoding="utf-8") == text, rel


def test_hidden_tests_never_appear_in_prompts():
    tasks = load_visible()
    hidden = grader.load_hidden()
    for tid, h in hidden.items():
        for line in h.get("hidden_tests", []):
            assert line not in tasks[tid].prompt


def test_world_answers_behave_as_labeled():
    """Correct answers pass both checks. visible_fail answers fail the visible check.
    hidden_fail answers pass the visible check and fail the hidden one."""
    tasks = load_visible()
    hidden = grader.load_hidden()
    world = [json.loads(x) for x in (DATA / "fake" / "world.jsonl").read_text().splitlines()]
    for w in world:
        t, h = tasks[w["id"]], hidden[w["id"]]
        for a in w["correct"]:
            assert visible_check(t, a) and grader.correct(t, h, a), w["id"]
        for a in w["visible_fail"]:
            assert not visible_check(t, a), w["id"]
            assert not grader.correct(t, h, a), w["id"]
        for a in w["hidden_fail"]:
            assert visible_check(t, a) and not grader.correct(t, h, a), (w["id"], a)
