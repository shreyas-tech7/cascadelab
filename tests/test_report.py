"""The README, chart and results page come from the results files and stay in step with them."""

from __future__ import annotations

import copy
import re

from cascadelab import report


def test_generated_files_match_results():
    assert report.main(check=True) == 0


def test_readme_table_numbers_come_from_results():
    r = report.load(report.MAIN)
    table = report.results_table(r)
    readme = (report.ROOT / "README.md").read_text(encoding="utf-8")
    assert table in readme
    for name in report.ORDER:
        s = r["splits"]["heldout"][name]
        row = next(line for line in table.splitlines() if line.startswith(f"| {s['label']} |"))
        assert report.pct(s["accuracy"]) in row
        assert report.usd(s["cost_per_1000_usd"]) in row
        assert report.pct(s["escalation_rate"]) in row


def test_readme_states_date_models_and_price_date():
    r = report.load(report.MAIN)
    line = report.context_line(r)
    assert r["manifest"]["recorded_on"] in line
    assert r["prices_checked_on"] in line
    for model in (r["manifest"]["cheap"], r["manifest"]["strong"]):
        assert model in line


def test_chart_is_built_from_results():
    r = report.load(report.MAIN)
    svg = report.chart_svg(r)
    for name in report.ORDER:
        assert r["splits"]["heldout"][name]["label"] in svg
    moved = copy.deepcopy(r)
    moved["splits"]["heldout"]["cheap_only"]["accuracy"] = 0.51
    assert report.chart_svg(moved) != svg


def test_chart_draws_one_point_and_one_interval_per_strategy():
    svg = report.chart_svg(report.load(report.MAIN))
    assert len(re.findall(r'data-strategy="', svg)) >= len(report.ORDER)


def test_cost_block_says_more_when_a_strategy_costs_more():
    r = report.load(report.MAIN)
    moved = copy.deepcopy(r)
    strong = moved["splits"]["heldout"]["strong_only"]["cost_per_1000_usd"]
    moved["splits"]["heldout"]["cheap_only"]["cost_per_1000_usd"] = 2 * strong
    assert "100.0% more than strong only" in report.cost_block(moved)


def test_usd_puts_the_sign_before_the_dollar():
    assert report.usd(-0.5) == "-$0.5000"
    assert report.usd(0.25) == "$0.2500"
