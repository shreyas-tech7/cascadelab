# Human steps

Steps that only Shreyas can do, in order.

Release commit: `RELEASE_SHA` (the same SHA is in CHANGELOG.md).

1. Open a pull request from `claude/project-thread-z94q4h` into `main`. Read the diff. Merge with a merge commit, so the release commit stays in the history of `main`.
2. Create the tag on the release commit: `git fetch origin`, then `git tag -a v0.1.0-rc1 RELEASE_SHA -m "Release candidate 1"`, then `git push origin v0.1.0-rc1`. Or create a pre-release with that tag on GitHub.
3. Run the secret scan once more: `gitleaks git -v .` (the repo's `.gitleaks.toml` allows only the fixture request hashes).
4. Fill in the About box from `docs/GITHUB_ABOUT.md` and the topics from `docs/topics.txt`, if the coordinator could not.
5. Upload `docs/social-preview.png` under Settings, General, Social preview.
6. Make the repo public when ready. All history becomes public at that moment.
7. Turn on Pages from `docs/` if you want the results page online. It opens from disk without it.
8. Pin the repo or list it in the profile README.
9. Publish to PyPI with trusted publishing, if you want the package there. The name `cascadelab` was free on 2026-11-23.
10. Record real models. This is the step that turns the worked example into real numbers.
    1. Pick a free cheap and strong pair. A later record says Groq moved its Llama models to enterprise pricing, so check Groq's free tier first. The community list at https://github.com/cheahjs/free-llm-api-resources tracks free OpenAI-compatible endpoints. OpenRouter's `:free` models also work with `--provider openrouter`.
    2. Create the free key. Export it as `GROQ_API_KEY` or `OPENROUTER_API_KEY`, or add it as a repository secret and run the Record workflow by hand.
    3. Run `cascadelab record --provider groq --cheap SMALL_MODEL --strong LARGE_MODEL --limit 300`. It resumes, so repeat it across days until it reports every call recorded (180 tasks times 6 calls).
    4. Add the two model names and their prices to `data/prices.json` with the date you checked them.
    5. Run `cascadelab run --fixtures groq`, then point `report.MAIN` at the new fixtures and run `cascadelab readme`. Update the README status line by hand, because it says the numbers come from fakes.
11. Where Hugging Face is reachable, run `pip install -e ".[embed]"` and `CASCADELAB_FASTEMBED=1 cascadelab run` for the learned embedding router.
12. Hand-check a sample of the tasks in `data/tasks/visible.jsonl` against `data/tasks/hidden.jsonl`, then tick that line in the README's "How this was built" section.
13. Install the toolkit skills (ponytail, caveman, humanizer) in a normal session, if you want them for later work.
14. Decide whether `docs/build/BUILD_PROMPT.md` stays public.
