# PROJECT_CONTEXT

**What:** cascadelab measures how much LLM cascades and routers save on tasks a program can check
(math answers, JSON extraction, small Python functions), and what they cost in accuracy and latency.
Every number replays offline from fixture files.

**Status:** v0.1.0-rc1 build. Results come from a fake model pair because no provider key exists in
the build session. Record mode is written and tested against a local server.

**Stack:** Python 3.11+, numpy, pytest, ruff. Optional FastEmbed (hash embedder is the default).

**Commands**

- `./init.sh`: venv, install, lint, link check, frozen-task check, all tests offline.
- `cascadelab make-tasks --check`: the task files match the generator and `data/FROZEN.json`.
- `cascadelab record --provider fake --seed 0`: write fake fixtures. `--provider groq` needs `GROQ_API_KEY`.
- `cascadelab run`: replay every strategy, write `results/*.json`.
- `cascadelab readme` (same as `report`): write README tables, `docs/index.html`, `docs/DECISION_GUIDE.md`. Add `--check` in CI.
- `cascadelab demo`: short replay transcript.

**Layout**

- `src/cascadelab/tasks.py` visible task data only. `grader.py` hidden checks only.
- `checks.py` parsers, visible checks, subprocess test runner. `models.py` fixture cache and record mode.
- `fakes.py` fake model pair. `strategies.py` the strategies. `router.py` hash embedder plus logistic regression.
- `evaluate.py` replay harness, oracle, scoring. `metrics.py`, `costs.py`, `report.py`, `cli.py`, `taskgen.py`.
- `data/tasks/` frozen tasks and split. `data/fake/world.jsonl` answers the fakes draw from. `data/prices.json` dated prices.
- `fixtures/fake-seed0`, `fixtures/fake-seed1` recorded fake calls. `results/` replay output.

**Rules**

- The visibility rule: strategy-side modules never import `grader`, `fakes`, `taskgen` or `evaluate`. `tests/test_leak.py`.
- The router trains on `split["dev"]` only. `tests/test_router.py`.
- Never edit `data/tasks/*` by hand. Change `taskgen.py`, rerun `make-tasks`, and log why in DECISIONS.md.
- Never type numbers into README.md or docs/DECISION_GUIDE.md.

**Skills that fit:** superpowers (TDD, debugging, verification), ponytail and ponytail-review, humanizer for docs.

**Do not read:** `.venv/`, `fixtures/*/*.jsonl` (large, generated), `results/*-tasks.jsonl`, `docs/build/`.
