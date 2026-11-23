# HANDOVER

State on 2026-11-23: release candidate v0.1.0-rc1 is built and pushed on `claude/project-thread-z94q4h`. Every Done-means item passes on the fake model pair. The release commit SHA is in CHANGELOG.md and docs/HUMAN_STEPS.md.

To resume: read docs/build/BUILD_PROMPT.md, then PROGRESS.md. Run `./init.sh`. It should print "all checks passed".

What a new session would do next:
1. If a free provider key exists, follow step 10 in docs/HUMAN_STEPS.md to record real models, then regenerate the README.
2. Build the budget mode stretch from docs/PROPOSALS.md, with a test that its pick never reads held-out results.

Rules that bite: never type numbers into the README (run `cascadelab readme`). Never edit fixtures or frozen task files by hand. Strategy modules must not import grader, fakes, taskgen or evaluate.
