# Release check

Run on 2026-11-23, before the release candidate.

| Step | Result |
| --- | --- |
| Ponytail review | The ponytail skill is not installed in this session. A fresh reviewer subagent that did not write the code did a least code review of every source, test, script and workflow file instead. Findings and fixes below. |
| Security audit | Skipped by the brief. No sign-in, personal data or payments. |
| `gitleaks git -v .` | no leaks found. `.gitleaks.toml` allows only the fixture request hashes, and a planted token is still caught |
| `pip-audit` | no known vulnerabilities (the local `cascadelab` package is editable, so it is skipped) |
| `ruff check --select S` | passes. Five S311 findings for seeded random generators carry a reason. Two asserts in `taskgen.py` became `ValueError` |
| `actionlint` | passes |
| `scripts/check_links.py` | 0 problems. External links are listed as not checked |
| Humanizer | not installed. README and docs were checked by hand: no em dashes, no semicolons in prose, no listed buzzwords |
| Outside check | a fresh subagent cloned the repo, ran `./init.sh` and checked each Done-means item. Results below |
| GitHub Actions | CI passed on the branch push |
| `git status` clean, flags match | yes, see `feature_list.json` |

## Code review findings and fixes

| Finding | Fix | Test |
| --- | --- | --- |
| Code that called `exit(0)` before the tests ran counted as passing, in the visible check and in the hidden grader. | The test file ends with a fixed exit code, and only that code passes. | `test_code_that_exits_early_does_not_pass` |
| A forked child held the pipe open until the timeout and outlived the temp folder. stdin was inherited. | Own process group killed at the end, no stdin, a process limit. | `test_code_cannot_read_stdin_or_fork` |
| Provider keys were in the job env of the record workflow, so install and tests ran with them. | Keys go to the record step only. | actionlint |
| Five different unparseable answers all normalized to `none` and counted as agreement. | Escalate when any sample fails to parse. | `test_agreement_on_unparseable_answers_escalates` |
| The decision guide said agreement pays off when the strong model costs many times more per call, which the numbers contradicted. | Prints the break-even escalation rate from the results. | `test_decision_guide_states_the_agreement_break_even` |
| `--date` defaulted to a fixed day. | Defaults to today. | none needed |
| Router note and pairing note were fixed text inside generated blocks. | Both now depend on the numbers. The router note compares gain over cheap only per split. | `readme --check` |
| The `fit` guard could never fire from the harness. | It takes the split and refuses held-out tasks. | `test_fit_refuses_a_split_whose_parts_overlap` |
| Record mode: a partial last line broke resume, null content was stored, 5xx got no retry. | All three fixed. | `test_partial_last_line_is_dropped_and_resume_works`, `test_null_content_is_refused`, `test_server_errors_back_off_too` |
| Two pairs of strategies shared a marker shape. The axis label always said held-out. | Six distinct shapes, split-aware label. | `test_each_strategy_has_its_own_marker_shape` |
| The oracle was built in two passes. | One comprehension. | replay tests |

Left as is: `tests/test_replay.py` runs twice in one process, so the cache on `run_tests` could hide subprocess nondeterminism. CI covers it by running `cascadelab run` in a fresh process and checking `git diff results/`.

## Outside check

| Done-means | Result |
| --- | --- |
| 1. Offline tests with fixtures and a fake pair whose cheap model fails on a known subset | pass |
| 2. Every strategy end to end, byte for byte twice | pass, two runs and the committed files share one SHA-256 |
| 3. README table with intervals, cost, latency, escalation, dates and models | pass, all six held-out rows checked by hand |
| 4. No hidden data reaches strategy code | **fail at first.** The lock patched only `open` and `Path.read_text`, and a strategy using `Path.read_bytes` got through. The poison test could not fail. Fixed with an audit hook lock and a parametrized test that plugs a leaky strategy into `run_strategies` for ten routes (`read_text`, `read_bytes`, `Path.open`, `open`, `io.open`, `os.open`, a relative path, the fake world file, the grader, a subprocess). I reran the checker's `read_bytes` break and the suite now fails. |
| 5. Router trains on development only | pass, removing the refusal fails a test |
| 6. Chart built from the results file | pass, coordinates checked against the JSON |
| 7. Part 1 quality bar | pass |

The checker also found two doc claims that overstated things. Interview answer 3 said most cheap failures show in the answer, but the visible check caught 9 of 19 on the held-out split. Answer 8 described the old lock. Both are corrected, and the walkthrough's claim that only `evaluate.py` imports the grader now has its own test.
