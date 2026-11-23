# BLOCKERS

| Date | What failed | Exact error | What I did instead |
| --- | --- | --- | --- |
| 2026-11-23 | Record mode on Groq and OpenRouter | `curl: (56) CONNECT tunnel failed, response 403` for api.groq.com and openrouter.ai. No `GROQ_API_KEY` or `OPENROUTER_API_KEY` in the environment | Fake model pair with fixtures (`fixtures/fake-seed0`, `fake-seed1`). Record mode tested against a local HTTP server. Manual step in docs/HUMAN_STEPS.md |
| 2026-11-23 | Gemini endpoint as a second option | `403` from generativelanguage.googleapis.com with no key | Same fallback |
| 2026-11-23 | FastEmbed model download | `CONNECT tunnel failed, response 403` for huggingface.co | Hash embedder (`router.hash_embed`), named `hash-512` in every results file |
| 2026-11-23 | osv-scanner and semgrep | api.osv.dev and semgrep.dev answer `CONNECT tunnel failed, response 403` | pip-audit and `ruff check --select S`, as the prompt allows |
| 2026-11-23 | Groq list prices | A record dated 2026-08-26 says Groq moved both Llama models to enterprise pricing | Used the last public list prices ($0.05/$0.08 and $0.59/$0.79 per 1M tokens), labeled with the source and that caveat in data/prices.json |
| 2026-11-23 | gh, PR, tags, repo settings | The brief says the proxy refuses them | The coordinator opens the PR, merges and tags. Values are in docs/GITHUB_ABOUT.md and docs/topics.txt |
