# DECISIONS

- 2026-11-23 Name: `cascadelab`. PyPI `https://pypi.org/pypi/cascadelab/json` answered 404 and npm `https://registry.npmjs.org/cascadelab` answered 404 on 2026-11-23. The repo already has this name.
- 2026-11-23 Branch: the session may push only `claude/project-thread-z94q4h`, so I built there instead of `claude/build-cascadelab` (brief rule 11).
- 2026-11-23 Models: no key and the provider hosts answer 403, so every result comes from a fake model pair (`fake-cheap`, `fake-strong`). Options weighed: wait for a key (nobody can add one), use a local model (too big for the 2 GB rule), or fakes. Fakes keep every pipeline step real and honest about being simulated.
- 2026-11-23 Fake behavior: the cheap fake fails more often on tasks with more steps, more fields or harder functions. Some wrong answers fail the visible check and some only the hidden one (shares in `fakes.VISIBLE_SHARE`). These shares set how well "cascade on check" can do, so the README says the cascade numbers describe the simulation, not real models.
- 2026-11-23 Prices: the fakes are priced as llama-3.1-8b-instant and llama-3.3-70b-versatile at Groq's last public list prices, dated, for comparison only.
- 2026-11-23 Task set: 180 tasks, 60 per family, built by a seeded generator (`taskgen.py`, seed 20261123) and frozen by SHA-256 in `data/FROZEN.json`. The generator executes each Python reference, its edge bug and its plain bug, and refuses to write a task where the edge bug does not pass the examples and fail a hidden test.
- 2026-11-23 Split: 60% dev and 40% held out, stratified by family (108 and 72), fixed by seed before any run.
- 2026-11-23 Math visible check: the answer must be a bare number. That is the only run-time check a math answer has, so it catches format failures and nothing else.
- 2026-11-23 Agreement: k = 5. Keep the first cheap answer only if all five agree after normalization, else escalate. Unanimity is the simplest rule and the brief says "escalate when they disagree". The five samples run in parallel, so latency is the slowest sample.
- 2026-11-23 Code agreement compares normalized source text, not behavior, because running every sample on inputs we invent would need inputs from somewhere.
- 2026-11-23 Router: 512-dim signed hash of words and word pairs, logistic regression with balanced class weights and L2 = 1, threshold 0.5. A threshold tuned on dev would need cross-validation on 108 tasks, and the brief keeps the router small.
- 2026-11-23 Router labels: whether the cheap greedy answer fails the hidden check, on dev tasks only. Training labels from dev are not run-time leakage: the router never sees a held-out label.
- 2026-11-23 Oracle: calls only the model it needs (cheap when the cheap answer is right). It is an upper bound and sits in `evaluate.py`, not in `strategies.py`.
- 2026-11-23 Latency: the sum (or max for parallel samples) of recorded call latencies. Check time is left out, because wall-clock time would break byte-identical replay. The limits section says so.
- 2026-11-23 Intervals: Wilson 95% for accuracy, paired bootstrap (2000 resamples, seed 0) for differences against strong-only. Cost and latency come from fixed fixture values, so they carry no sampling interval except the bootstrap of the cost difference.
- 2026-11-23 Second seed: the fake has a seed. Seed 1 is a second, independent draw of the same fake, reported next to seed 0.
- 2026-11-23 Skills: `npx skills` installs were not tried because earlier builds in this project had them denied. Ponytail and caveman were cloned to /tmp, scanned with skill-scanner and read by hand.
