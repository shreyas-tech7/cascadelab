# Walkthrough

This is a plain tour of every file. Read it top to bottom once. Then use it as a map.

## The big picture

The lab asks one question. When is a cheap model enough?

It has 180 tasks. A program can grade each one. Each task has a visible part and a hidden part. Strategies see the visible part only. The grader sees the hidden part.

Model answers come from fixtures. A fixture is a recorded call, stored by a hash of the request. Replay reads fixtures, so a run needs no network and gives the same bytes every time.

The fixtures in this repo come from two fake models. The fakes stand in for real models until someone adds a free key.

## The flow of one run

1. `cascadelab run` loads the visible tasks, the split and the fixtures.
2. It trains the router on the development split.
3. It runs every strategy on visible tasks. Each strategy returns an answer and the calls it made.
4. The grader scores each answer with the hidden checks.
5. The metrics code adds up accuracy, cost, latency and escalation, with intervals.
6. It writes `results/<fixtures>.json` and one line per task to `results/<fixtures>-tasks.jsonl`.
7. `cascadelab report` reads those files and rewrites the README blocks, the chart and the results page.

## Source code: `src/cascadelab/`

### `taskgen.py`

This file makes the task set. It runs once, and its output is frozen.

There are three families. Math word problems come from ten templates. JSON extraction asks for fields from a short text with a schema. Code tasks ask for a small Python function.

Each code template has three bodies. `ref` is the right answer. `edge` passes the examples but fails a hidden test. `plain` fails an example. The fake models use `edge` and `plain` as wrong answers, so some wrong code passes the visible check and some does not.

`make_split` puts 60% of each family in development and 40% in held-out. A seed fixes the split.

`render` builds four files: the visible tasks, the hidden checks, the split and the fake world. `write` saves them.

### `tasks.py`

This file loads tasks for the strategy side. `VisibleTask` holds only the id, the family, the prompt and the visible checks. It has no field for the gold answer.

`SYSTEM` holds one system prompt per family. `messages()` builds the chat messages for a call.

### `checks.py`

Visible checks live here. A real system could run them at run time.

- `parse_number` reads a math answer. It accepts a plain number, with an optional dollar sign and commas.
- `parse_json` and `schema_ok` check JSON against the task schema.
- `run_tests` runs code against the example tests. It uses a subprocess with `-I -S`, a temp folder, a 5 second timeout, and CPU and memory limits.
- `visible_check` picks the right check for a task.
- `normalize` turns an answer into a form that two answers can be compared in. The agreement cascade uses it.

### `grader.py`

Hidden checks live here. `load_hidden` reads the gold answers and hidden tests. `correct` scores one answer. For code it runs the examples and the hidden tests.

Only `evaluate.py` imports this file. A test proves that.

### `models.py`

This file handles model calls.

- `request_key` hashes the model, the messages, the temperature and the sample number.
- `FixtureStore` reads and writes fixtures. `get` returns a recorded call or raises `MissingFixture`.
- `plan` lists every call a full run needs: one greedy call per model, plus extra cheap samples for the agreement cascade.
- `record` fills the missing calls from a provider. It skips calls that exist, so it resumes.
- `OpenAICompatible` calls Groq or OpenRouter with the standard library. It reads the key from an environment variable. It waits and retries on a 429, doubling the wait each time.

### `fakes.py`

The fake model pair.

`cheap_fail_rate` sets how often the cheap fake fails. Harder tasks fail more often: more steps in math, more fields and distractor sentences in JSON, a higher level in code. The strong fake fails at a quarter of that rate, plus 1%.

`VISIBLE_SHARE` sets which share of wrong answers the visible check catches. This one number decides how well the cascade on a check can do. It is the main way the fakes differ from real models.

`FakeProvider` draws from a seeded random generator, keyed by the seed, the model and the task. So the same seed always gives the same answers.

### `strategies.py`

The strategies that a real system could run.

- `cheap_only` and `strong_only` make one call.
- `cascade_check` asks the cheap model, runs the visible check, and asks the strong model if the check fails.
- `cascade_agree` takes five cheap samples. If they all agree after `normalize`, it keeps the answer. Otherwise it asks the strong model. Samples run in parallel, so latency counts the slowest one.
- `make_routed` wraps a trained router. The router decides before any call.

This file imports `checks`, `models`, `router` and `tasks` only.

### `router.py`

The learned router.

`hash_embed` turns text into a 512 number vector. It hashes words and word pairs. It needs no download.

`Router.fit` trains a logistic regression on development tasks. The label says whether the cheap answer failed the hidden check. It raises an error if any task is outside the development split.

`escalate` returns true when the predicted chance of failure is at least 0.5.

With `CASCADELAB_FASTEMBED=1`, `embed` uses a small learned model instead. That needs a download from Hugging Face.

### `costs.py`

`load_prices` reads `data/prices.json`. `call_cost` prices one call from its token counts.

### `metrics.py`

- `wilson` gives a 95% interval for accuracy.
- `paired_bootstrap` resamples tasks and compares two strategies on the same tasks.
- `unpaired_bootstrap` resamples each strategy on its own. It exists to show how much pairing helps.
- `percentile` gives latency p50 and p95.

### `evaluate.py`

The replay harness. It runs strategies first, then scores them. This order keeps hidden data away from strategy code.

The oracle router lives here, because it needs hidden results. It picks the cheap answer when that answer is right and the strong answer when it is not. It sets the ceiling.

`run` returns the result dict. `write` saves it with sorted keys and rounded floats, so the bytes match across runs.

### `report.py`

This file turns results into text and pictures. Every number in the README comes from here.

`fill` replaces the text between `<!-- name:start -->` and `<!-- name:end -->` markers. `chart_svg` draws the cost and accuracy chart. `index_html` builds the static results page. `decision_guide` writes `docs/DECISION_GUIDE.md`. `main(check=True)` fails if any generated file is out of date.

### `cli.py`

The `cascadelab` command. It has `make-tasks`, `record`, `run`, `report` (also called `readme`) and `demo`.

## Data: `data/`

- `tasks/visible.jsonl`: what strategies may see.
- `tasks/hidden.jsonl`: gold answers and hidden tests.
- `tasks/split.json`: which tasks are development and which are held-out.
- `fake/world.jsonl`: the right and wrong answers the fakes pick from.
- `FROZEN.json`: a hash for each file above. `make-tasks --check` compares them.
- `prices.json`: the dated price table and its source.

## Fixtures and results

- `fixtures/fake-seed0/` and `fixtures/fake-seed1/`: two independent draws of the fake pair. Each has a manifest that says it is simulated.
- `results/`: the output of `cascadelab run`. Tests check that a fresh replay matches these files.

## Tests: `tests/`

- `conftest.py`: blocks the network for every test.
- `test_network_guard.py`: proves the block works.
- `test_tasks.py`: counts, split sizes, frozen hashes, and that no hidden text appears in a prompt.
- `test_checks.py`: each visible check on good and bad answers.
- `test_fakes.py`: the cheap fake fails on a known subset, and the strong fake fails less.
- `test_strategies.py`: each strategy's logic on hand-made calls.
- `test_router.py`: the router refuses held-out tasks and trains on development only.
- `test_leak.py`: strategy code never imports the grader, never opens hidden files, and gives the same output when hidden data is poisoned.
- `test_replay.py`: two runs give the same bytes, and the committed results match.
- `test_record.py`: record mode against a local test server: resume, headers, temperatures, backoff.
- `test_metrics.py`: the interval code.
- `test_report.py`: the README, chart and page match the results files.

## Scripts and setup

- `init.sh`: makes the virtual env, installs, lints, checks links and frozen tasks, runs the tests.
- `scripts/check_links.py`: checks every relative link and anchor in the docs.
- `scripts/make_social_preview.py`: draws `docs/social-preview.png` with plain Python.
- `.github/workflows/ci.yml`: runs the same steps as `init.sh` on GitHub.

## Notes for people and agents

- `PROJECT_CONTEXT.md`, `PROGRESS.md`, `HANDOVER.md` and `feature_list.json` let a new session pick up the work.
- `DECISIONS.md` lists each choice and why.
- `BLOCKERS.md` lists what the build machine could not reach.
- `docs/HUMAN_STEPS.md` lists what only Shreyas can do.
