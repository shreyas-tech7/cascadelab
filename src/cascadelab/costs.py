"""Turn token counts into dollars with the dated list price table in data/prices.json.

The dollars are for comparison only. Every run in this repo cost $0.
"""

from __future__ import annotations

import json
from pathlib import Path

from .models import Call
from .tasks import DATA


def load_prices(data_dir: Path = DATA) -> dict:
    return json.loads((data_dir / "prices.json").read_text(encoding="utf-8"))


def call_cost(call: Call, prices: dict) -> float:
    p = prices["models"][call.model]
    return (call.prompt_tokens * p["input"] + call.completion_tokens * p["output"]) / 1e6
