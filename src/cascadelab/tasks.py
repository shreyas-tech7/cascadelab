"""Visible task data. This is everything a strategy may see at run time.

Hidden data (gold answers and hidden tests) lives in `grader.py` and never enters this module.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data"

SYSTEM = {
    "math": "Solve the word problem. Answer with the final number only.",
    "json": "Extract the fields. Answer with one JSON object only, with exactly the listed keys.",
    "code": "Write the Python function. Answer with the code only, with no tests and no prose.",
}


@dataclass(frozen=True)
class VisibleTask:
    id: str
    family: str
    prompt: str
    visible: dict

    def messages(self) -> list[dict]:
        return [{"role": "system", "content": SYSTEM[self.family]}, {"role": "user", "content": self.prompt}]


def load_visible(data_dir: Path = DATA) -> dict[str, VisibleTask]:
    out = {}
    for line in (data_dir / "tasks" / "visible.jsonl").read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        out[r["id"]] = VisibleTask(r["id"], r["family"], r["prompt"], r["visible"])
    return out


def load_split(data_dir: Path = DATA) -> dict:
    return json.loads((data_dir / "tasks" / "split.json").read_text(encoding="utf-8"))
