# PROGRESS

Branch: `claude/project-thread-z94q4h`.

## Done
- F01 to F09: initializer, frozen tasks, fake pair, strategies, metrics, router split test, leak test, replay harness, record mode (local server test).
- F10 to F11: report with chart, static results page, decision guide, demo transcript, README generator with `--check`.
- F12: CI (green on the branch), manual record workflow, issue templates, CONTRIBUTING, CHANGELOG, topics, About text, social preview.
- F13: WALKTHROUGH, INTERVIEW_QA (15 answers), DECISIONS.
- F14: release check (fresh reviewer and outside check, all findings fixed or logged in docs/RELEASE_CHECK.md), HUMAN_STEPS.

## Next
- Human steps in docs/HUMAN_STEPS.md: PR and merge, tag, record real models.
- Stretch, not built: budget mode (docs/PROPOSALS.md).

## Blockers
- Record mode: no key, provider hosts 403. Fakes stand in.
- FastEmbed: huggingface.co 403. Hash embedder stands in.

## Last ./init.sh
- 2026-11-23: 60 passed, all checks passed.
