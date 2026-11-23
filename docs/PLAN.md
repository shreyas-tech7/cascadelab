# Plan

The brief in `docs/build/BUILD_PROMPT.md` is the spec. This plan turns its build order into steps. Each step ends with its tests green and `./init.sh` passing.

1. Initializer. Memory files, `init.sh`, MIT license, `.gitignore`, `.env.example`, gitleaks config, saved brief.
2. Task set. Three families (math, JSON extraction, small Python functions) from seeded templates in `taskgen.py`. Visible parts in `tasks/visible.jsonl`, hidden parts in `tasks/hidden.jsonl`, a 60/40 split stratified by family, all frozen by hash in `FROZEN.json`. Tests: counts, split, frozen hashes, no hidden text in prompts.
3. Visible checks and grader. `checks.py` for run time checks, `grader.py` for hidden scoring, code run in a limited subprocess.
4. Fake model pair. Seeded, with failure rates that grow with difficulty and a set share of wrong answers that the visible check catches. Test: the cheap fake fails on a known subset.
5. Fixture store. Request hash keys, JSONL per model, a manifest, resumable record mode, an OpenAI-compatible client with 429 backoff. Tested against a local server.
6. Strategies. Cheap only, strong only, cascade on a visible check, cascade on agreement (k = 5), learned router. Oracle router in the harness.
7. Cost model and metrics. Dated price table, Wilson intervals, paired and unpaired bootstrap, latency percentiles.
8. Router. Hash embedding plus numpy logistic regression, trained on development tasks only. Test: `fit` refuses held-out tasks.
9. Leak test. Import scan, a lock on hidden data during strategy runs, and a poison test.
10. Replay harness. `cascadelab run` writes results twice to the same bytes, for two fake seeds.
11. Report. `cascadelab readme` writes README blocks, the chart, `docs/index.html`, the decision guide and the demo transcript. `--check` in CI.
12. README, study-later kit, release check, hand-off.

Assumptions (also in `DECISIONS.md`):

- Record mode may be blocked. Then the fake pair stands in, and the README says so in its status line.
- Prices come from a public page read on the build day, with its date and a caveat.
- The held-out split stays small (72 tasks), so the README shows intervals and a second seed.
