# Tooling

| Tool | Source | Version or commit | Why | Check |
| --- | --- | --- | --- | --- |
| superpowers skills | already in the session (obra/superpowers) | session copy | writing-plans, TDD, verification, code review | used, not installed |
| ponytail | https://github.com/DietrichGebert/ponytail | ebd8654 | least code, and ponytail-review for the release check | cloned to /tmp, `skill-scanner scan --fail-on-severity high`: 0 findings. Read by hand, not installed |
| caveman | https://github.com/JuliusBrussee/caveman | b89752f | terse progress notes | skill-scanner: 0 high, 1 info. Read by hand. Not used for files |
| skill-scanner | PyPI cisco-ai-skill-scanner | latest on 2026-11-23 | vet skills | installed with `uv tool install` |
| gitleaks | github.com/zricethezav/gitleaks/v8 | v8.30.1 | secret scan before commits and on history | `go install` |
| actionlint | github.com/rhysd/actionlint | v1.7.12 | lint workflow files | `go install` |
| pip-audit | PyPI | 2.10.1 | dependency check | `uv tool install` |
| ruff | PyPI | from `.[dev]` | lint, format, `--select S` security rules | installed in .venv |
| graphify | PyPI graphifyy | not installed | only for resume runs on more than 30 source files | not needed: about 15 source files |
| find-skills, humanizer | vercel-labs/skills, blader/humanizer | not installed | earlier builds had `npx skills` denied | humanizer rules applied by hand: plain words, no em dashes, no semicolons |
| OmniRoute, litellm | GITHUB_REPOS.md | not installed | need a key | listed in docs/HUMAN_STEPS.md |
| LlamaFirewall, garak, Prompt Guard | GITHUB_REPOS.md | not installed | no prompt input from users and models are fakes, so nothing to guard | not needed |
| crawl4ai, playwright-mcp | GITHUB_REPOS.md | not installed | no crawling and no web UI to drive | not needed |
| anatomy, rtk | GITHUB_REPOS.md | not installed | stretch figure, optional token saver | skipped |
| security-audit | cloudflare/security-audit-skill | not used | no sign-in, personal data or money | prompt says skip |
