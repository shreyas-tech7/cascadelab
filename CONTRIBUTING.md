# Contributing

Thanks for looking. This is a small lab, so the rules are short.

1. Run `./init.sh` before and after your change. It installs, lints, checks links, checks the frozen task set and runs every test offline.
2. Write a test that fails first. Name the broken case in its docstring.
3. Never type a number into the README. Change the code or the results, then run `cascadelab readme`.
4. Strategy code may read visible task data only. Never import `grader`, `fakes`, `taskgen` or `evaluate` from a strategy module. `tests/test_leak.py` checks this.
5. Never train or tune the router on the held-out split. `tests/test_router.py` checks this.
6. Never edit a fixture by hand. Record it again with `cascadelab record`.
7. Never change a frozen task file by hand. Change `taskgen.py`, run `cascadelab make-tasks`, and explain why in `DECISIONS.md`, because every result depends on the task set.
8. New ideas go in `docs/PROPOSALS.md` first.

Writing rules for docs: active voice, plain words, no em dashes, no dashes as punctuation and no semicolons in prose.
