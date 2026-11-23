# Interview questions and answers

Each answer points at the code and at a results file. The numbers come from `results/fake-seed0.json`, the held-out split of 72 tasks, unless an answer says otherwise. They come from the fake model pair, so they show the method, not facts about real models.

## 1. What does cascadelab measure?

When a cheap model is enough. It runs six strategies on 180 tasks that a program can grade, and reports accuracy with a 95% interval, cost per 1,000 tasks, latency p50 and p95, and escalation rate. The loop is `evaluate.run` in `src/cascadelab/evaluate.py`.

## 2. What is the difference between a cascade and a router?

A router decides before any call. It looks at the task text and sends it to one model. A cascade calls the cheap model first, looks at the answer, and moves up only when a signal says the answer is bad. So a router pays for one call, and a cascade sometimes pays for two. In exchange, a cascade gets to see the answer, which is far more informative than the question. Compare `make_routed` and `cascade_check` in `src/cascadelab/strategies.py`.

## 3. Why does escalation on a checker work so well?

Because a checker reads the answer, and many cheap failures show in the answer. A math answer that is not a number, JSON that breaks the schema, or code that fails an example test all fail the visible check. On the held-out split the check caught 9 of the 19 cheap failures, and a strong call on those 9 tasks fixed 8 of them. The cascade on a visible check escalates only 12.5% of tasks and lifts accuracy from 73.6% (cheap only) to 84.7%, at $0.0148 per 1,000 tasks against $0.0662 for strong only. The learned router escalates 33.3% and reaches 79.2%, because it guesses from the question alone.

The limit is the share of wrong answers that the check cannot see. In the fakes that share is a setting, `fakes.VISIBLE_SHARE`. Code that handles the examples but fails a hidden edge case passes the visible check, so the cascade keeps it.

## 4. Why does the agreement cascade cost more than the strong model alone here?

It always pays for five cheap samples, and then escalates when they disagree. On the held-out split it escalated 68.1% of tasks, so it paid for five cheap calls plus a strong call on most tasks. Its cost was $0.0738 per 1,000 tasks against $0.0662 for strong only. Agreement is a useful signal (97.2% accuracy here), but only when samples are cheap relative to the strong model and the cheap model agrees with itself often. On code it is also strict, because `checks.normalize` compares source text, so two correct programs written differently count as a disagreement.

## 5. Why do you need a held-out split for the router?

The router learns which tasks the cheap model fails. Measured on the tasks it trained on, it looks great: 90.7% on the development split. On held-out tasks it scores 79.2%. That gap is overfit. `Router.fit` in `src/cascadelab/router.py` raises an error for any task outside the development split, and `tests/test_router.py` checks that the trained weights do not move when held-out data changes.

## 6. Why paired bootstrap?

Every strategy runs on the same tasks. Some tasks are easy for everyone and some are hard for everyone. A paired bootstrap resamples tasks and compares the two strategies on the same resample, so that shared difficulty cancels out. Resampling each strategy on its own counts that difficulty twice as noise.

The repo shows the effect in `evaluate.pairing`. The cascade on a check and cheap only share their outcome on 88.9% of held-out tasks. The paired interval on their difference runs from +4.2 to +18.1 points and excludes zero. The unpaired interval runs from -2.8 to +25.0 points and includes zero. Same data, different conclusion. Against strong only the two strategies share less, so pairing helps less.

## 7. What do list prices hide?

Several things. Free tiers and rate limits change what a run really costs. Enterprise contracts and batch discounts change the price per token. Cached prompt pricing makes repeated system prompts cheap. Latency and retries cost time, and time costs money. Tokens counted by one tokenizer are not tokens counted by another. And prices move: the table in `data/prices.json` holds Groq's last public prices for two Llama models, but a later record says Groq moved them to enterprise pricing. That is why the table carries a date and a source, and why the README calls the dollars a comparison only.

## 8. How do you prove that no hidden data reaches strategy code?

Two ways, both in `tests/test_leak.py`. First, an import scan: no strategy-side module imports `grader`, `fakes`, `taskgen` or `evaluate`, and only `evaluate.py` imports the grader at all. Second, a lock built on a Python audit hook (`sys.addaudithook`). While strategies run, any open of `hidden.jsonl` or `world.jsonl` raises an error, whichever file API does it: `open`, `io.open`, `os.open`, `Path.read_text`, `Path.read_bytes` or `Path.open`. Starting any process other than the code test runner raises too. A parametrized test plugs a leaky strategy into `run_strategies` once for each of those routes and checks that every one is caught.

An earlier version patched only `open` and `Path.read_text`. An outside check got past it with `read_bytes`, which is why the lock now sits at the audit hook level.

## 9. How does replay stay byte for byte?

Every model call is stored by a SHA-256 of the model, the messages, the temperature and the sample number (`models.request_key`). Replay looks calls up and never calls a model. Results are written with sorted keys and floats rounded to six places (`evaluate.write`). Latency is the sum of recorded call latencies, not a clock, so it does not change between runs. `tests/test_replay.py` runs twice and compares bytes, and CI checks that `git diff results/` is empty after a fresh run.

## 10. Why fake models?

The build machine had no provider key and the provider hosts were blocked. Fakes let every part of the method run and be tested offline. `fakes.FakeProvider` draws from a seeded generator. The cheap fake fails more on harder tasks (`cheap_fail_rate`), and the strong fake fails at a quarter of that rate plus 1%. Record mode for real free models is written and tested against a local server in `tests/test_record.py`.

## 11. What does the oracle tell you?

It is the ceiling for any router between these two models. It knows from the hidden check whether the cheap answer is right. It reaches 98.6% at $0.0218 per 1,000 tasks, with 26.4% of tasks sent to the strong model. The learned router sits far below that, which says the question text alone carries little signal about cheap failure here. The oracle lives in `evaluate.evaluate_split`, not in `strategies.py`, because it reads hidden results.

## 12. How noisy are these numbers?

Quite noisy. The held-out split has 72 tasks, so a single accuracy has an interval about 20 points wide. A second independent draw of the fakes (`results/fake-seed1.json`) moves cheap only from 73.6% to 65.3% and strong only from 94.4% to 88.9%. Read differences of a few points as noise.

## 13. How do code answers run safely?

`checks.run_tests` writes the code and tests to a temp folder and runs `python -I -S` in a subprocess with a 5 second timeout, a CPU limit, a 512 MB memory limit and no stdin. The child runs in its own process group, which is killed at the end, so a forked grandchild cannot linger. The program must end by exiting with a fixed code after the last test, so code that calls `exit(0)` early fails. It is not a full sandbox, and the README says so.

## 14. How would you put this in production?

Start with the cascade on a visible check wherever a cheap check exists: schema validation, unit tests, a parser. Log every escalation with its reason. Use the logs to measure the share of wrong answers that pass the check, because that share sets your ceiling. Add a router only where no check exists, and train it on logged outcomes, held out by time. Recheck prices monthly.

## 15. What would you do next?

Record a real free model pair, because the fakes decide the numbers. Add a budget mode that picks the cheapest strategy that meets a target accuracy on the development split and reports it on held-out data. Try the learned embedding router where Hugging Face is reachable. Add a task family with no visible check, to show where routers earn their place. These are in `docs/PROPOSALS.md`.
