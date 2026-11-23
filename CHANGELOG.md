# Changelog

## v0.1.0-rc1 (2026-11-23)

Release commit: 80c1a5c319345e91663de1b682d3afd3d7838e96

- A frozen task set of 180 program-graded tasks in three families, with visible checks for strategies and hidden checks for scoring, and a 60/40 split stratified by family.
- A seeded fake model pair whose cheap model fails more on harder tasks, with fixtures for two independent seeds.
- A fixture store keyed by request hash that replays byte for byte, and a resumable record mode for Groq and OpenRouter.
- Six strategies: cheap only, strong only, cascade on a visible check, cascade on agreement, a learned router trained on the development split only, and an oracle upper bound.
- Metrics with Wilson intervals, paired bootstrap against strong only, a dated cost model, latency percentiles and escalation rate.
- Leak tests that prove no hidden data reaches strategy code.
- A README, chart, static results page and decision guide written from the results files.
