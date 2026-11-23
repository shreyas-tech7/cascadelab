# Environment

Probed on 2026-11-23 with `curl -sS -o /dev/null -w '%{http_code}' -m 10 <url>`.

| Host | Result | Use |
| --- | --- | --- |
| https://api.groq.com/openai/v1/models | CONNECT tunnel failed, 403 | record mode, blocked |
| https://openrouter.ai/api/v1/models | CONNECT tunnel failed, 403 | record mode, blocked |
| https://generativelanguage.googleapis.com/v1beta/models | 403 (no key) | not used |
| https://huggingface.co | CONNECT tunnel failed, 403 | FastEmbed model, blocked |
| https://storage.googleapis.com | 400 (host reachable) | not needed |
| https://api.osv.dev | CONNECT tunnel failed, 403 | osv-scanner, skipped |
| https://semgrep.dev | CONNECT tunnel failed, 403 | semgrep, skipped |
| https://pypi.org/pypi/cascadelab/json | 404 | name is free |
| https://registry.npmjs.org/cascadelab | 404 | name is free |

No provider key variable was set (`GROQ_API_KEY`, `OPENROUTER_API_KEY`).

Machine: Intel(R) Xeon(R) Processor @ 2.30GHz, 4 cores, Python 3.11 in `.venv` (uv), Linux.
