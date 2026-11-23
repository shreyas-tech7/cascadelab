"""Command line: make-tasks, record, run, report, readme, demo."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import evaluate, taskgen
from .models import FIXTURES, ROOT, FixtureStore, OpenAICompatible, record
from .strategies import K
from .tasks import DATA, load_visible

RESULTS = ROOT / "results"
MAIN_FIXTURES = ["fake-seed0", "fake-seed1"]


def cmd_make_tasks(args) -> int:
    frozen = DATA / "FROZEN.json"
    if args.check:
        want = json.loads(frozen.read_text())
        got = {rel: taskgen.sha(text) for rel, text in taskgen.render().items()}
        on_disk = {rel: taskgen.sha((DATA / rel).read_text(encoding="utf-8")) for rel in want}
        ok = want == got == on_disk
        print("task files match the generator and FROZEN.json" if ok else "task files changed")
        return 0 if ok else 1
    hashes = taskgen.write(DATA)
    frozen.write_text(json.dumps(hashes, indent=1, sort_keys=True) + "\n")
    print(f"wrote {len(hashes)} files")
    return 0


def _provider(args):
    if args.provider == "fake":
        from .fakes import FakeProvider

        return FakeProvider(args.seed)
    return OpenAICompatible.named(args.provider)


def cmd_record(args) -> int:
    out = (
        Path(args.out)
        if args.out
        else FIXTURES / (f"fake-seed{args.seed}" if args.provider == "fake" else args.provider)
    )
    out.mkdir(parents=True, exist_ok=True)
    manifest = out / "manifest.json"
    if not manifest.exists():
        cheap, strong = ("fake-cheap", "fake-strong") if args.provider == "fake" else (args.cheap, args.strong)
        info = {"provider": args.provider, "cheap": cheap, "strong": strong, "recorded_on": args.date}
        if args.provider == "fake":
            info |= {"seed": args.seed, "note": "simulated models, not real LLM output"}
        manifest.write_text(json.dumps(info, indent=1, sort_keys=True) + "\n")
    store = FixtureStore(out)
    tasks = list(load_visible().values())
    made = record(store, _provider(args), tasks, args.k, args.limit)
    need = len(tasks) * (args.k + 1)
    print(f"{out.name}: {made} new calls, {len(store.calls)} of {need} recorded")
    return 0


def cmd_run(args) -> int:
    for name in args.fixtures or MAIN_FIXTURES:
        result, rows = evaluate.run(FIXTURES / name)
        main, _ = evaluate.write(result, rows, Path(args.out) if args.out else RESULTS)
        print("wrote", main.relative_to(ROOT) if main.is_relative_to(ROOT) else main)
    return 0


def cmd_report(args) -> int:
    from . import report

    return report.main(check=args.check)


def cmd_demo(args) -> int:
    from . import report

    return report.demo()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="cascadelab", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("make-tasks", help="write the frozen task set, or check it with --check")
    p.add_argument("--check", action="store_true")
    p.set_defaults(fn=cmd_make_tasks)
    p = sub.add_parser("record", help="fill missing fixtures from a provider (resumes)")
    p.add_argument("--provider", choices=["fake", "groq", "openrouter"], default="fake")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--cheap", default="llama-3.1-8b-instant")
    p.add_argument("--strong", default="llama-3.3-70b-versatile")
    p.add_argument("--k", type=int, default=K)
    p.add_argument("--limit", type=int, default=None, help="stop after this many new calls")
    p.add_argument("--date", default="2026-11-23", help="recorded_on date for a new manifest")
    p.add_argument("--out", default=None)
    p.set_defaults(fn=cmd_record)
    p = sub.add_parser("run", help="replay strategies from fixtures and write results/")
    p.add_argument("--fixtures", nargs="*")
    p.add_argument("--out", default=None)
    p.set_defaults(fn=cmd_run)
    for name in ("report", "readme"):
        p = sub.add_parser(name, help="write README tables, docs/index.html and the decision guide")
        p.add_argument("--check", action="store_true", help="fail if any generated file is out of date")
        p.set_defaults(fn=cmd_report)
    p = sub.add_parser("demo", help="replay a few held-out tasks and print what each strategy did")
    p.set_defaults(fn=cmd_demo)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
