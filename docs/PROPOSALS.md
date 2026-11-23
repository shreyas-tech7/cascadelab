# Proposals

Ideas that are not built yet. Each needs a test plan before code.

- **Real models.** Record a free cheap and strong pair, then rerun. This is the most important next step, because the fakes decide the numbers now. See `docs/HUMAN_STEPS.md`.
- **Budget mode.** Pick the cheapest strategy that meets a target accuracy on the development split, then report how it does on the held-out split. Test: the pick never reads held-out results.
- **A family with no visible check.** For example short free text answers graded by a hidden key. This is where a router should beat a cascade on a check.
- **Learned embeddings for the router.** `CASCADELAB_FASTEMBED=1` with BAAI/bge-small-en-v1.5, where Hugging Face is reachable.
- **Semantic agreement for code.** Compare programs by their outputs on the example inputs instead of their source text.
- **Threshold sweep.** Plot the learned router's cost and accuracy as its threshold moves, picked on the development split.
