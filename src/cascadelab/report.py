"""Write every generated file from the results files. Nobody types these numbers.

Generated: the marked blocks in README.md, docs/chart.svg, docs/index.html,
docs/DECISION_GUIDE.md and docs/DEMO.md. `cascadelab readme --check` fails when any of
them differs from what the results files say.
"""

from __future__ import annotations

import contextlib
import html
import io
import json
import re
from pathlib import Path

from .evaluate import ORDER
from .models import ROOT

RESULTS = ROOT / "results"
SPLIT_NAMES = {"heldout": "held-out", "dev": "development"}
MAIN = "fake-seed0"
SECOND = "fake-seed1"
COLORS = {  # validated with the dataviz palette checker, light and dark
    "cheap_only": ("#2a78d6", "#3987e5"),
    "strong_only": ("#eb6834", "#d95926"),
    "cascade_check": ("#1baf7a", "#199e70"),
    "cascade_agree": ("#eda100", "#c98500"),
    "learned_router": ("#e87ba4", "#d55181"),
    "oracle_router": ("#6250d6", "#9085e9"),
}
SHAPES = {
    "cheap_only": "circle",
    "strong_only": "square",
    "cascade_check": "diamond",
    "cascade_agree": "triangle",
    "learned_router": "down",
    "oracle_router": "cross",
}


def load(name: str) -> dict:
    return json.loads((RESULTS / f"{name}.json").read_text(encoding="utf-8"))


def pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def signed_pts(x: float) -> str:
    return f"{100 * x:+.1f}"


def usd(x: float) -> str:
    return f"-${-x:.4f}" if x < 0 else f"${x:.4f}"


def models_line(r: dict) -> str:
    m = r["manifest"]
    return (
        f"`{m['cheap']}` (priced as {r['priced_as'][m['cheap']]}) and `{m['strong']}` "
        f"(priced as {r['priced_as'][m['strong']]})"
    )


def context_line(r: dict, split: str = "heldout") -> str:
    m = r["manifest"]
    n = r["splits"][split]["strong_only"]["n"]
    return (
        f"{'Held-out' if split == 'heldout' else 'Development'} split, {n} tasks. Models: {models_line(r)}. "
        f"Fixtures `{r['fixtures']}` recorded {m['recorded_on']} by the {m['provider']} provider, fake seed "
        f"{m.get('seed', 'n/a')}. Price table checked {r['prices_checked_on']}. Agreement cascade k = "
        f"{r['agreement_k']}. Router embedder `{r['router']['embedder']}`. Bootstrap {r['bootstrap']['reps']} "
        f"resamples, seed {r['bootstrap']['seed']}."
    )


def results_table(r: dict, split: str = "heldout") -> str:
    rows = [
        "| Strategy | Accuracy (95% CI) | vs strong only, points (paired 95% CI) | Cost per 1,000 tasks | "
        "Latency p50 / p95 | Escalation rate | Calls per task |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for name in ORDER:
        s = r["splits"][split][name]
        lo, hi = s["accuracy_ci95"]
        d, dlo, dhi = s["vs_strong_accuracy"]
        vs = "baseline" if name == "strong_only" else f"{signed_pts(d)} ({signed_pts(dlo)} to {signed_pts(dhi)})"
        rows.append(
            f"| {s['label']} | {pct(s['accuracy'])} ({pct(lo)} to {pct(hi)}) | {vs} | "
            f"{usd(s['cost_per_1000_usd'])} | {s['latency_p50_ms']:.0f} / {s['latency_p95_ms']:.0f} ms | "
            f"{pct(s['escalation_rate'])} | {s['calls_per_task']:.2f} |"
        )
    return "\n".join(rows)


def cost_block(r: dict) -> str:
    s = r["splits"]["heldout"]
    strong = s["strong_only"]["cost_per_1000_usd"]
    lines = [
        f"Strong only costs {usd(strong)} per 1,000 held-out tasks at the dated list prices. "
        "Here is what each other strategy costs, and how much it saves against strong only:",
        "",
    ]
    for name in ORDER:
        if name == "strong_only":
            continue
        c = s[name]["cost_per_1000_usd"]
        cd, clo, chi = s[name]["vs_strong_cost_per_1000_usd"]
        change = f"{pct(1 - c / strong)} saved" if c <= strong else f"{pct(c / strong - 1)} more than strong only"
        lines.append(
            f"- {s[name]['label']}: {usd(c)} per 1,000 tasks, {change} "
            f"(paired difference {usd(cd)}, 95% CI {usd(clo)} to {usd(chi)})."
        )
    lines += [
        "",
        "These dollars are a comparison only. The runs in this repo cost $0: the fixtures come from "
        "the fake model pair, and record mode targets free tiers.",
    ]
    return "\n".join(lines)


def seeds_block(r0: dict, r1: dict) -> str:
    rows = [
        "| Strategy | Accuracy, seed "
        + str(r0["manifest"]["seed"])
        + " | Accuracy, seed "
        + str(r1["manifest"]["seed"])
        + " | Cost per 1,000, seed "
        + str(r0["manifest"]["seed"])
        + " | Cost per 1,000, seed "
        + str(r1["manifest"]["seed"])
        + " |",
        "| --- | --- | --- | --- | --- |",
    ]
    for name in ORDER:
        a, b = r0["splits"]["heldout"][name], r1["splits"]["heldout"][name]
        rows.append(
            f"| {a['label']} | {pct(a['accuracy'])} | {pct(b['accuracy'])} | "
            f"{usd(a['cost_per_1000_usd'])} | {usd(b['cost_per_1000_usd'])} |"
        )
    return "\n".join(rows)


def paired_block(r: dict) -> str:
    def width(ci):
        return 100 * (ci[1] - ci[0])

    a, b = r["pairing"]["cascade_check_vs_cheap_only"], r["pairing"]["cascade_check_vs_strong_only"]
    gained = width(b["unpaired_ci95"]) - width(b["paired_ci95"]) > 1
    tail = (
        "Pairing narrows that interval too, because the two strategies fail on many of the same tasks."
        if gained
        else "Pairing gains little there, because the fake models fail independently of each other. Real models "
        "tend to fail on the same hard tasks, which makes pairing worth more."
    )
    return (
        f"Pairing helps most when two strategies share outcomes. The cascade on a visible check and cheap only "
        f"have the same outcome on {pct(a['same_outcome_share'])} of held-out tasks. The paired 95% interval on "
        f"their accuracy difference is {width(a['paired_ci95']):.1f} points wide, and resampling them separately "
        f"gives {width(a['unpaired_ci95']):.1f} points. Against strong only the two share outcomes on "
        f"{pct(b['same_outcome_share'])} of tasks, and the widths are {width(b['paired_ci95']):.1f} paired and "
        f"{width(b['unpaired_ci95']):.1f} unpaired. {tail}"
    )


def router_block(r: dict) -> str:
    dev, held = r["splits"]["dev"]["learned_router"], r["splits"]["heldout"]["learned_router"]
    gain = {
        sp: r["splits"][sp]["learned_router"]["accuracy"] - r["splits"][sp]["cheap_only"]["accuracy"]
        for sp in ("dev", "heldout")
    }
    verdict = (
        "The gain shrinks on tasks it never saw, which is the overfit the held-out split exists to show."
        if gain["heldout"] < gain["dev"]
        else "The gain holds on tasks it never saw."
    )
    return (
        f"The learned router scores {pct(dev['accuracy'])} on the development split it trained on and "
        f"{pct(held['accuracy'])} on the held-out split. The splits differ in difficulty, so compare its gain over "
        f"cheap only instead: {signed_pts(gain['dev'])} points on development and {signed_pts(gain['heldout'])} on "
        f"held-out. {verdict} It trained on {len(r['router']['train_ids'])} development tasks with the "
        f"`{r['router']['embedder']}` embedder."
    )


# ---------------------------------------------------------------- chart


def _nice(x: float) -> float:
    for step in (0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0):
        if x <= step * 5:
            return step
    return 1.0


def chart_svg(r: dict, split: str = "heldout") -> str:
    s = r["splits"][split]
    w, h, left, right, top, bottom = 760, 460, 70, 200, 30, 60
    pw, ph = w - left - right, h - top - bottom
    xmax_raw = max(v["cost_per_1000_usd"] for v in s.values())
    xstep = _nice(xmax_raw)
    xmax = xstep * (int(xmax_raw / xstep) + 1)
    ymin = min(0.5, int(min(v["accuracy_ci95"][0] for v in s.values()) * 10) / 10)

    def X(c):
        return left + pw * c / xmax

    def Y(a):
        return top + ph * (1 - (a - ymin) / (1 - ymin))

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
        f'role="img" aria-labelledby="t d" font-family="system-ui, -apple-system, Segoe UI, sans-serif">',
        '<title id="t">Accuracy against cost per 1,000 tasks</title>',
        f'<desc id="d">{html.escape(context_line(r, split))}</desc>',
        "<style>",
        ".bg{fill:#fcfcfb}.ink{fill:#0b0b0b}.ink2{fill:#52514e}.grid{stroke:#e4e3df;stroke-width:1}"
        ".axis{stroke:#9a9993;stroke-width:1}.ci{stroke-width:2;stroke-linecap:round}.ring{stroke:#fcfcfb;stroke-width:2}",
        "".join(f".s-{n}{{fill:{c[0]};stroke:{c[0]}}}" for n, c in COLORS.items()),
        "@media (prefers-color-scheme: dark){.bg{fill:#1a1a19}.ink{fill:#f0efec}.ink2{fill:#c3c2b7}"
        ".grid{stroke:#383835}.axis{stroke:#6b6a64}.ring{stroke:#1a1a19}"
        + "".join(f".s-{n}{{fill:{c[1]};stroke:{c[1]}}}" for n, c in COLORS.items())
        + "}",
        "</style>",
        f'<rect class="bg" width="{w}" height="{h}" rx="8"/>',
    ]
    a = ymin
    while a <= 1.0001:
        y = Y(a)
        out.append(f'<line class="grid" x1="{left}" x2="{left + pw}" y1="{y:.1f}" y2="{y:.1f}"/>')
        out.append(
            f'<text class="ink2" x="{left - 8}" y="{y + 4:.1f}" font-size="12" text-anchor="end">{pct(a)}</text>'
        )
        a = round(a + 0.1, 10)
    c = 0.0
    while c <= xmax + 1e-12:
        x = X(c)
        out.append(f'<line class="axis" x1="{x:.1f}" x2="{x:.1f}" y1="{top + ph}" y2="{top + ph + 5}"/>')
        out.append(
            f'<text class="ink2" x="{x:.1f}" y="{top + ph + 20}" font-size="12" text-anchor="middle">${c:.2f}</text>'
        )
        c = round(c + xstep, 10)
    out.append(f'<line class="axis" x1="{left}" x2="{left + pw}" y1="{top + ph}" y2="{top + ph}"/>')
    out.append(
        f'<text class="ink" x="{left + pw / 2}" y="{h - 14}" font-size="13" text-anchor="middle">'
        "Cost per 1,000 tasks (USD, dated list prices, comparison only)</text>"
    )
    out.append(
        f'<text class="ink" x="16" y="{top + ph / 2}" font-size="13" text-anchor="middle" '
        f'transform="rotate(-90 16 {top + ph / 2})">Accuracy, {SPLIT_NAMES[split]} (95% CI)</text>'
    )
    for i, name in enumerate(ORDER):
        v = s[name]
        x, y = X(v["cost_per_1000_usd"]), Y(v["accuracy"])
        lo, hi = Y(v["accuracy_ci95"][0]), Y(v["accuracy_ci95"][1])
        tip = html.escape(
            f"{v['label']}: accuracy {pct(v['accuracy'])} ({pct(v['accuracy_ci95'][0])} to "
            f"{pct(v['accuracy_ci95'][1])}), {usd(v['cost_per_1000_usd'])} per 1,000 tasks, "
            f"escalation {pct(v['escalation_rate'])}"
        )
        out.append(f'<g class="s-{name}" data-strategy="{name}"><title>{tip}</title>')
        out.append(f'<line class="ci s-{name}" x1="{x:.1f}" x2="{x:.1f}" y1="{lo:.1f}" y2="{hi:.1f}"/>')
        shape = SHAPES[name]
        if shape == "circle":
            out.append(f'<circle class="ring s-{name}" cx="{x:.1f}" cy="{y:.1f}" r="6"/>')
        elif shape == "square":
            out.append(f'<rect class="ring s-{name}" x="{x - 6:.1f}" y="{y - 6:.1f}" width="12" height="12" rx="2"/>')
        elif shape == "diamond":
            out.append(
                f'<path class="ring s-{name}" d="M{x:.1f} {y - 8:.1f}L{x + 8:.1f} {y:.1f}L{x:.1f} {y + 8:.1f}L{x - 8:.1f} {y:.1f}Z"/>'
            )
        elif shape == "triangle":
            out.append(
                f'<path class="ring s-{name}" d="M{x:.1f} {y - 8:.1f}L{x + 8:.1f} {y + 6:.1f}L{x - 8:.1f} {y + 6:.1f}Z"/>'
            )
        elif shape == "down":
            out.append(
                f'<path class="ring s-{name}" d="M{x:.1f} {y + 8:.1f}L{x + 8:.1f} {y - 6:.1f}L{x - 8:.1f} {y - 6:.1f}Z"/>'
            )
        else:
            out.append(f'<path class="ring s-{name}" d="M{x - 3:.1f} {y - 8:.1f}h6v5h5v6h-5v5h-6v-5h-5v-6h5Z"/>')
        out.append("</g>")
        ly = top + 14 + 22 * i
        out.append(f'<rect class="s-{name}" x="{left + pw + 18}" y="{ly - 9}" width="12" height="12" rx="3"/>')
        out.append(
            f'<text class="ink" x="{left + pw + 36}" y="{ly + 1}" font-size="12">{html.escape(v["label"])}</text>'
        )
    out.append("</svg>")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- pages


def html_table(r: dict, split: str) -> str:
    head = "<tr><th>Strategy</th><th>Accuracy (95% CI)</th><th>vs strong, points (paired 95% CI)</th>"
    head += "<th>Cost per 1,000</th><th>p50 / p95 latency</th><th>Escalation</th></tr>"
    body = []
    for name in ORDER:
        s = r["splits"][split][name]
        d, dlo, dhi = s["vs_strong_accuracy"]
        vs = "baseline" if name == "strong_only" else f"{signed_pts(d)} ({signed_pts(dlo)} to {signed_pts(dhi)})"
        body.append(
            f"<tr><td>{html.escape(s['label'])}</td><td>{pct(s['accuracy'])} ({pct(s['accuracy_ci95'][0])} to "
            f"{pct(s['accuracy_ci95'][1])})</td><td>{vs}</td><td>{usd(s['cost_per_1000_usd'])}</td>"
            f"<td>{s['latency_p50_ms']:.0f} / {s['latency_p95_ms']:.0f} ms</td><td>{pct(s['escalation_rate'])}</td></tr>"
        )
    return f"<table><thead>{head}</thead><tbody>{''.join(body)}</tbody></table>"


def index_html(r0: dict, r1: dict, guide: str) -> str:
    guide_html = "".join(f"<li>{html.escape(line[2:])}</li>" for line in guide.splitlines() if line.startswith("- "))
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>cascadelab results</title>
<style>
:root{{--bg:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--line:#e4e3df}}
@media (prefers-color-scheme: dark){{:root{{--bg:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--line:#383835}}}}
body{{background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif;margin:0 auto;max-width:980px;padding:24px 16px}}
p.note{{color:var(--ink2)}}
table{{border-collapse:collapse;width:100%;margin:12px 0 28px;font-size:14px}}
th,td{{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left}}
.wrap{{overflow-x:auto}} svg{{max-width:100%;height:auto}}
</style>
</head>
<body>
<h1 id="top">cascadelab results</h1>
<p class="note">Simulated models. Every number below comes from the fake model pair, replayed from fixtures,
and written by <code>cascadelab report</code> from the results files.</p>
<h2 id="chart">Accuracy against cost, held-out split</h2>
<p class="note">{html.escape(context_line(r0))}</p>
<div class="wrap">{chart_svg(r0)}</div>
<h2 id="table">Held-out table</h2>
<div class="wrap">{html_table(r0, "heldout")}</div>
<h2 id="dev">Development split (the router trained here, so its row is in-sample)</h2>
<div class="wrap">{html_table(r0, "dev")}</div>
<h2 id="seed1">Second fake seed, held-out split</h2>
<p class="note">{html.escape(context_line(r1))}</p>
<div class="wrap">{html_table(r1, "heldout")}</div>
<h2 id="guide">Decision guide</h2>
<ul>{guide_html}</ul>
<p class="note">Source files: results/{MAIN}.json and results/{SECOND}.json.</p>
</body>
</html>
"""


def decision_guide(r: dict) -> str:
    s = r["splits"]["heldout"]
    st = s["strong_only"]
    ratio = s["cheap_only"]["cost_per_1000_usd"] / st["cost_per_1000_usd"]
    best = [n for n in ORDER if n not in ("strong_only", "oracle_router", "cheap_only")]
    cheaper_ok = [
        n
        for n in best
        if s[n]["vs_strong_accuracy"][1] >= -0.05 and s[n]["cost_per_1000_usd"] < st["cost_per_1000_usd"]
    ]
    lines = [
        "# Decision guide",
        "",
        "Generated by `cascadelab report` from `results/" + MAIN + ".json`. The numbers come from the fake model "
        "pair, so treat them as a worked example of the method, not as facts about real models.",
        "",
        "## Rules of thumb",
        "",
        f"- Start from strong only ({pct(st['accuracy'])} held-out accuracy, {usd(st['cost_per_1000_usd'])} per "
        f"1,000 tasks). Every other strategy is judged by the paired difference against it.",
        f"- A cascade on a visible check is the first thing to try when your task has a check: it kept "
        f"{pct(1 - s['cascade_check']['escalation_rate'])} of tasks on the cheap model and cost "
        f"{usd(s['cascade_check']['cost_per_1000_usd'])} per 1,000 tasks. Its accuracy is "
        f"{pct(s['cascade_check']['accuracy'])}, because it can only catch failures that the check can see.",
        f"- A cascade on agreement needs no checker, but it pays for {r['agreement_k']} cheap samples on every task. "
        f"Here it cost {usd(s['cascade_agree']['cost_per_1000_usd'])} per 1,000 tasks, against "
        f"{usd(st['cost_per_1000_usd'])} for strong only, and escalated {pct(s['cascade_agree']['escalation_rate'])} "
        f"of tasks. One cheap call costs about {pct(ratio)} of one strong call here, so {r['agreement_k']} cheap "
        f"samples cost {pct(r['agreement_k'] * ratio)} of a strong call. It saves money only when it escalates "
        f"fewer than {pct(max(0.0, 1 - r['agreement_k'] * ratio))} of tasks.",
        f"- The learned router escalated {pct(s['learned_router']['escalation_rate'])} of tasks before any cheap "
        f"call and reached {pct(s['learned_router']['accuracy'])}. It needs labeled development data, and it "
        f"overfits: {pct(r['splits']['dev']['learned_router']['accuracy'])} on its own training split.",
        f"- The oracle router ({pct(s['oracle_router']['accuracy'])} for {usd(s['oracle_router']['cost_per_1000_usd'])}) "
        "is the ceiling for any router with these two models. Nobody can build it. Use it to see how much room is left.",
        "- If an interval on the paired difference crosses zero, you have not shown a difference. Get more tasks "
        "before you ship.",
        "",
        "## Strategies within 5 points of strong only at the low end of their interval, and cheaper",
        "",
    ]
    if cheaper_ok:
        lines += [
            f"- {s[n]['label']}: {pct(s[n]['accuracy'])}, {usd(s[n]['cost_per_1000_usd'])} per 1,000 tasks."
            for n in cheaper_ok
        ]
    else:
        lines.append("- None on this run.")
    return "\n".join(lines) + "\n"


def demo_text() -> str:
    r = load(MAIN)
    rows = [json.loads(x) for x in (RESULTS / f"{MAIN}-tasks.jsonl").read_text().splitlines()]
    held = [x for x in rows if x["split"] == "heldout"]
    picks = []
    for fam in ("math", "json", "code"):
        picks += sorted({x["task"] for x in held if x["task"].startswith(fam)})[:2]
    out = [f"replaying {MAIN}: {context_line(r)}", ""]
    out.append(f"{'task':10s} " + " ".join(f"{n:>14s}" for n in ORDER))
    for t in picks:
        cells = []
        for n in ORDER:
            x = next(y for y in held if y["task"] == t and y["strategy"] == n)
            cells.append(f"{('ok' if x['correct'] else 'WRONG') + (' esc' if x['escalated'] else ''):>14s}")
        out.append(f"{t:10s} " + " ".join(cells))
    out.append("")
    out.append("held-out summary:")
    for n in ORDER:
        s = r["splits"]["heldout"][n]
        out.append(
            f"  {s['label']:30s} accuracy {pct(s['accuracy']):>6s}  cost/1k {usd(s['cost_per_1000_usd'])}  "
            f"escalated {pct(s['escalation_rate']):>6s}"
        )
    return "\n".join(out) + "\n"


def demo() -> int:
    print(demo_text(), end="")
    return 0


def demo_md() -> str:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        demo()
    return (
        "# Demo\n\nA terminal transcript of `cascadelab demo`, regenerated by `cascadelab report`. It needs no key "
        "and no network: it reads `results/" + MAIN + "-tasks.jsonl`, which `cascadelab run` replays from the "
        "fixtures.\n\n```text\n$ cascadelab demo\n" + buf.getvalue() + "```\n\nThe static results page is "
        "[index.html](index.html). Open it from disk in any browser.\n"
    )


def fill(text: str, name: str, body: str) -> str:
    pat = re.compile(rf"(<!-- {name}:start -->\n).*?(<!-- {name}:end -->)", re.S)
    if not pat.search(text):
        raise ValueError(f"README has no {name} block")
    return pat.sub(lambda m: m.group(1) + body + "\n" + m.group(2), text)


def outputs() -> dict[Path, str]:
    r0, r1 = load(MAIN), load(SECOND)
    guide = decision_guide(r0)
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for name, body in [
        ("context", context_line(r0)),
        ("results", results_table(r0)),
        ("cost", cost_block(r0)),
        ("seeds", seeds_block(r0, r1)),
        ("paired", paired_block(r0)),
        ("router", router_block(r0)),
    ]:
        readme = fill(readme, name, body)
    return {
        ROOT / "README.md": readme,
        ROOT / "docs" / "chart.svg": chart_svg(r0),
        ROOT / "docs" / "index.html": index_html(r0, r1, guide),
        ROOT / "docs" / "DECISION_GUIDE.md": guide,
        ROOT / "docs" / "DEMO.md": demo_md(),
    }


def main(check: bool = False) -> int:
    stale = []
    for path, text in outputs().items():
        if check:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                stale.append(path.relative_to(ROOT))
        else:
            path.write_text(text, encoding="utf-8")
            print("wrote", path.relative_to(ROOT))
    if stale:
        print("out of date, run `cascadelab report`:", ", ".join(map(str, stale)))
        return 1
    if check:
        print("generated files match the results files")
    return 0
