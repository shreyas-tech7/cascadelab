"""Write the frozen task set: 60 math, 60 JSON extraction and 60 Python tasks.

Each task has a visible part (what a real system sees at run time) and a hidden part
(gold answer and hidden tests, for scoring only). The fake model world (correct and
wrong answers per task) goes to a third file that only `fakes.py` reads.
Run `cascadelab make-tasks` to rewrite the files. A test checks that the files match
this generator and the frozen hashes in data/FROZEN.json.
"""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

SEED = 20261123
NAMES = ["Mia", "Ravi", "Dana", "Omar", "Lena", "Kofi", "Ines", "Tariq", "Yuki", "Sam", "Ada", "Jon"]
CITIES = ["Denver", "Austin", "Leeds", "Pune", "Osaka", "Lagos", "Lima", "Oslo", "Perth", "Quito"]

# ---------------------------------------------------------------- math


def _math(rng: random.Random, t: int) -> tuple[str, int, int]:
    """Return (problem text, gold integer, number of steps)."""
    n = rng.choice(NAMES)
    if t == 0:
        a, p, b, q = rng.randint(2, 9), rng.randint(1, 4), rng.randint(1, 5), rng.randint(3, 9)
        cost = a * p + b * q
        r = (cost // 10 + 1) * 10 + rng.choice([0, 10, 40])
        text = (
            f"{n} buys {a} pencils at ${p} each and {b} notebooks at ${q} each. "
            f"{n} pays with ${r}. How many dollars of change does {n} get?"
        )
        return text, r - cost, 3
    if t == 1:
        v, h, w, g = rng.randint(40, 90), rng.randint(2, 5), rng.randint(30, 80), rng.randint(1, 4)
        text = (
            f"A train travels at {v} km per hour for {h} hours, then at {w} km per hour "
            f"for {g} hours. How many kilometers does it travel in total?"
        )
        return text, v * h + w * g, 3
    if t == 2:
        m = rng.choice([x for x in NAMES if x != n])
        d, y, a = rng.randint(2, 9), rng.randint(2, 8), rng.randint(12, 30)
        text = f"{n} is {d} years older than {m}. In {y} years {m} will be {a}. How old is {n} now?"
        return text, a - y + d, 2
    if t == 3:
        b, p = rng.randint(6, 20), rng.randint(10, 24)
        s, u = rng.randint(10, 40), rng.randint(5, 30)
        text = (
            f"A warehouse has {b} boxes with {p} items in each box. Workers ship {s} items on "
            f"Monday and {u} items on Tuesday. How many items are left?"
        )
        return text, b * p - s - u, 3
    if t == 4:
        p, d = rng.choice([40, 60, 80, 120, 200, 240]), rng.choice([10, 25, 50, 20])
        text = f"A jacket costs ${p}. It is on sale for {d} percent off. What is the sale price in dollars?"
        return text, p - p * d // 100, 2
    if t == 5:
        k, each, tip = rng.randint(3, 8), rng.randint(9, 30), rng.randint(2, 6)
        text = (
            f"{k} friends share a bill of ${k * each} equally, and each friend also adds a tip of ${tip}. "
            f"How many dollars does each friend pay?"
        )
        return text, each + tip, 2
    if t == 6:
        ln, w, x = rng.randint(5, 20), rng.randint(4, 15), rng.randint(1, 3)
        text = (
            f"A rectangular garden is {ln} meters long and {w} meters wide. A path {x} meters wide runs "
            f"around the outside of the garden. What is the area of the path in square meters?"
        )
        return text, (ln + 2 * x) * (w + 2 * x) - ln * w, 4
    if t == 7:
        a, wk, s, b, v = (
            rng.randint(5, 20),
            rng.randint(3, 8),
            rng.randint(10, 40),
            rng.randint(5, 15),
            rng.randint(2, 6),
        )
        text = (
            f"{n} saves ${a} each week for {wk} weeks, then spends ${s} on a game, then saves ${b} each "
            f"week for {v} more weeks. How many dollars does {n} have now?"
        )
        return text, a * wk - s + b * v, 4
    if t == 8:
        a, b = rng.randint(3, 12), rng.randint(6, 24)
        text = f"A baker makes {a} trays with {b} cookies on each tray. How many cookies does the baker make?"
        return text, a * b, 1
    k = rng.randint(3, 6)
    vals = [rng.randint(50, 100) for _ in range(k - 1)]
    target = (sum(vals) // k + 1) * k
    vals.append(target - sum(vals))
    while not 0 <= vals[-1] <= 150:
        vals = [rng.randint(50, 100) for _ in range(k - 1)]
        target = (sum(vals) // k + 1) * k
        vals.append(target - sum(vals))
    text = f"A student scored {', '.join(map(str, vals))} on {k} tests. What is the average score?"
    return text, target // k, 2


def _math_wrongs(rng: random.Random, gold: int) -> list[str]:
    deltas = rng.sample([1, -1, 2, -2, 5, -5, 10, -10], 3)
    return [str(gold + d) for d in deltas] + ["I need more information to answer this."]


# ---------------------------------------------------------------- json

SCHEMAS = {
    "order": {
        "order_id": "string",
        "customer": "string",
        "quantity": "integer",
        "unit_price": "number",
        "city": "string",
    },
    "person": {"name": "string", "age": "integer", "email": "string", "city": "string"},
    "event": {"title": "string", "date": "string", "start_hour": "integer", "room": "string"},
    "flight": {
        "flight_number": "string",
        "origin": "string",
        "destination": "string",
        "seats": "integer",
        "price": "number",
        "refundable": "boolean",
    },
    "product": {"sku": "string", "name": "string", "weight_kg": "number", "in_stock": "boolean", "tags": "array"},
    "invoice": {
        "invoice_id": "string",
        "vendor": "string",
        "total": "number",
        "due_date": "string",
        "paid": "boolean",
        "items_count": "integer",
        "currency": "string",
    },
}


def _date(rng: random.Random) -> str:
    return f"2026-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}"


def _json_task(rng: random.Random, kind: str) -> tuple[str, dict, int]:
    """Return (text, gold object, number of distractor numbers in the text)."""
    n, c, c2 = rng.choice(NAMES), rng.choice(CITIES), rng.choice(CITIES)
    noise = rng.randint(0, 2)
    extra = [
        f" The previous order last month had {rng.randint(2, 9)} units.",
        f" Support ticket {rng.randint(100, 999)} is still open.",
    ][:noise]
    if kind == "order":
        g = {
            "order_id": f"A{rng.randint(1000, 9999)}",
            "customer": f"{n} {rng.choice(['Kim', 'Ortiz', 'Patel', 'Berg'])}",
            "quantity": rng.randint(1, 12),
            "unit_price": rng.randint(100, 2500) / 100,
            "city": c,
        }
        text = (
            f"Order {g['order_id']} was placed by {g['customer']} for {g['quantity']} units of the blue widget "
            f"at ${g['unit_price']:.2f} each. Ship it to {g['city']}."
        )
    elif kind == "person":
        g = {"name": n, "age": rng.randint(19, 70), "email": f"{n.lower()}{rng.randint(1, 99)}@mail.test", "city": c}
        text = f"New member: {n}, {g['age']} years old, lives in {c}. Contact them at {g['email']}."
    elif kind == "event":
        g = {
            "title": rng.choice(["Budget review", "Design sync", "Hiring panel", "Launch prep"]),
            "date": _date(rng),
            "start_hour": rng.randint(8, 17),
            "room": f"Room {rng.randint(1, 30)}",
        }
        text = f"The {g['title']} meets on {g['date']} at {g['start_hour']}:00 in {g['room']}."
    elif kind == "flight":
        g = {
            "flight_number": f"{rng.choice(['QX', 'LB', 'TR'])}{rng.randint(100, 999)}",
            "origin": c,
            "destination": c2 if c2 != c else "Rome",
            "seats": rng.randint(1, 6),
            "price": rng.randint(9000, 60000) / 100,
            "refundable": rng.random() < 0.5,
        }
        ref = "is refundable" if g["refundable"] else "cannot be refunded"
        text = (
            f"Booked {g['seats']} seats on flight {g['flight_number']} from {g['origin']} to {g['destination']} "
            f"for ${g['price']:.2f} in total. The fare {ref}."
        )
    elif kind == "product":
        tags = rng.sample(["steel", "outdoor", "kitchen", "sale", "eco", "new"], rng.randint(1, 3))
        g = {
            "sku": f"SKU-{rng.randint(10000, 99999)}",
            "name": rng.choice(["Camp stove", "Water bottle", "Desk lamp", "Rain jacket"]),
            "weight_kg": rng.randint(1, 80) / 10,
            "in_stock": rng.random() < 0.6,
            "tags": tags,
        }
        stock = "in stock" if g["in_stock"] else "sold out"
        text = (
            f"Product {g['sku']}, the {g['name']}, weighs {g['weight_kg']} kg and is {stock}. Tags: {', '.join(tags)}."
        )
    else:
        g = {
            "invoice_id": f"INV-{rng.randint(100, 999)}",
            "vendor": f"{rng.choice(['North', 'Blue', 'Iron'])} Supply",
            "total": rng.randint(5000, 900000) / 100,
            "due_date": _date(rng),
            "paid": rng.random() < 0.4,
            "items_count": rng.randint(1, 40),
            "currency": rng.choice(["USD", "EUR", "GBP"]),
        }
        state = "has been paid" if g["paid"] else "is still unpaid"
        text = (
            f"Invoice {g['invoice_id']} from {g['vendor']} lists {g['items_count']} items for a total of "
            f"{g['total']:.2f} {g['currency']}, due {g['due_date']}. It {state}."
        )
    return text + "".join(extra), g, noise


def _json_wrongs(rng: random.Random, gold: dict, schema: dict) -> tuple[list[str], list[str]]:
    """Return (answers that fail the visible schema check, answers that pass it with a wrong value)."""
    keys = list(schema)
    k = rng.choice(keys)
    missing = {x: v for x, v in gold.items() if x != k}
    k2 = rng.choice(keys)
    bad_type = dict(gold)
    bad_type[k2] = str(gold[k2]) if schema[k2] != "string" else len(str(gold[k2]))
    invalid = [json.dumps(missing), json.dumps(bad_type), "Here is the data: " + json.dumps(gold)[:-1]]
    wrong = []
    for k3 in rng.sample(keys, 2):
        w = dict(gold)
        v = w[k3]
        if isinstance(v, bool):
            w[k3] = not v
        elif isinstance(v, int):
            w[k3] = v + rng.choice([1, 2, -1])
        elif isinstance(v, float):
            w[k3] = round(v * 10, 2)
        elif isinstance(v, list):
            w[k3] = v[:-1] if len(v) > 1 else v + ["misc"]
        else:
            w[k3] = v.split(" ")[0] + "x" if " " not in v else v.split(" ")[0]
        wrong.append(json.dumps(w))
    return invalid, wrong


# ---------------------------------------------------------------- code

CODE = [
    {
        "fn": "sum_divisible",
        "sig": "def sum_divisible(nums: list[int]) -> int:",
        "doc": "Return the sum of the integers in nums that are divisible by {C}. nums may hold negative numbers.",
        "cs": [2, 3, 4, 5, 7],
        "ref": "    return sum(x for x in nums if x % {C} == 0)",
        "edge": "    return sum(x for x in nums if x > 0 and x % {C} == 0)",
        "plain": "    return sum(x for x in nums if x % {C} != 0)",
        "ex": lambda c: [[c, c + 1, 2 * c], [1, 3 * c]],
        "hid": lambda c: [[], [-c, c], [-2 * c, 1], [0, c, 5 * c], [c + 1]],
        "level": 1,
    },
    {
        "fn": "count_long_words",
        "sig": "def count_long_words(s: str) -> int:",
        "doc": "Return how many words in s have more than {C} characters. Words are separated by any whitespace.",
        "cs": [2, 3, 4, 5, 6],
        "ref": "    return sum(1 for w in s.split() if len(w) > {C})",
        "edge": "    return sum(1 for w in s.split(' ') if len(w) > {C})",
        "plain": "    return sum(1 for w in s.split() if len(w) >= {C})",
        "ex": lambda c: ["a" * c + " " + "b" * (c + 1), "x " + "y" * (c + 2) + " z"],
        "hid": lambda c: ["", "a" * (c + 1) + "\t" + "b" * (c + 1), "q" * (c + 1) + "\n" + "r", "a" * c, "  "],
        "level": 1,
    },
    {
        "fn": "kth_largest",
        "sig": "def kth_largest(nums: list[int]) -> int | None:",
        "doc": "Return the {C}-th largest distinct value in nums, or None if nums has fewer than {C} distinct values.",
        "cs": [2, 3, 4, 5, 6],
        "ref": "    v = sorted(set(nums), reverse=True)\n    return v[{C} - 1] if len(v) >= {C} else None",
        "edge": "    v = sorted(nums, reverse=True)\n    return v[{C} - 1] if len(v) >= {C} else None",
        "plain": "    v = sorted(set(nums))\n    return v[{C} - 1] if len(v) >= {C} else None",
        "ex": lambda c: [list(range(1, c + 3)), list(range(10, 10 + 3 * (c + 1), 3))],
        "hid": lambda c: [[5] * (c + 1), [], [9, 9] + list(range(1, c + 1)), list(range(c, 0, -1)), [1]],
        "level": 2,
    },
    {
        "fn": "rotate_left",
        "sig": "def rotate_left(items: list) -> list:",
        "doc": "Return a new list with items rotated left by {C} positions. items may be shorter than {C} or empty.",
        "cs": [3, 4, 5, 7, 8],
        "ref": "    if not items:\n        return []\n    k = {C} % len(items)\n    return items[k:] + items[:k]",
        "edge": "    return items[{C}:] + items[:{C}]",
        "plain": "    if not items:\n        return []\n    k = {C} % len(items)\n    return items[-k:] + items[:-k]",
        "ex": lambda c: [list(range(c + 3)), list("abcdefghij"[: c + 4])],
        "hid": lambda c: [[], list(range(c + 2)), [7], [1, 2] if c % 2 else [1, 2, 3], list(range(2 * c + 3))],
        "level": 2,
    },
    {
        "fn": "capped_running_totals",
        "sig": "def capped_running_totals(nums: list[int]) -> list[int]:",
        "doc": "Return the running totals of nums, each capped at {C} (use min(total, {C})). Return [] for an empty list.",
        "cs": [10, 15, 20, 30, 50],
        "ref": "    out, t = [], 0\n    for x in nums:\n        t += x\n        out.append(min(t, {C}))\n    return out",
        "edge": "    if not nums:\n        return [0]\n    out, t = [], 0\n    for x in nums:\n        t += x\n        out.append(min(t, {C}))\n    return out",
        "plain": "    out, t = [], 0\n    for x in nums:\n        t += x\n        out.append(t)\n    return out",
        "ex": lambda c: [[c // 2, c // 2, c], [1, c]],
        "hid": lambda c: [[], [c + 5], [-1, c, 3], [0], [c, -c, 1]],
        "level": 1,
    },
    {
        "fn": "chunk",
        "sig": "def chunk(items: list) -> list[list]:",
        "doc": "Split items into consecutive chunks of size {C}. The last chunk may be shorter.",
        "cs": [2, 3, 4, 5, 6],
        "ref": "    return [items[i : i + {C}] for i in range(0, len(items), {C})]",
        "edge": "    return [items[i : i + {C}] for i in range(0, len(items) - len(items) % {C}, {C})]",
        "plain": "    return [items[i : i + {C} + 1] for i in range(0, len(items), {C} + 1)]",
        "ex": lambda c: [list(range(2 * c)), list(range(c))],
        "hid": lambda c: [[], list(range(c + 1)), list(range(3 * c - 1)), [1], list(range(c - 1))],
        "level": 1,
    },
    {
        "fn": "count_digit",
        "sig": "def count_digit(n: int) -> int:",
        "doc": "Return how many times the digit {C} appears in the integer n. n can be zero or negative.",
        "cs": [1, 2, 3, 7, 9],
        "ref": "    return str(abs(n)).count('{C}')",
        "edge": "    count = 0\n    while n > 0:\n        if n % 10 == {C}:\n            count += 1\n        n //= 10\n    return count",
        "plain": "    s = str(abs(n))\n    return len(s) - s.count('{C}')",
        "ex": lambda c: [int(f"{c}{c}5"), int(f"8{c}")],
        "hid": lambda c: [0, -int(f"{c}{c}"), int(f"{c}0{c}0{c}"), -5, int(f"1{c}")],
        "level": 2,
    },
    {
        "fn": "indices_above",
        "sig": "def indices_above(nums: list[int]) -> list[int]:",
        "doc": "Return the indices of the elements of nums that are greater than {C}, in order.",
        "cs": [0, 5, 10, 25, 100],
        "ref": "    return [i for i, x in enumerate(nums) if x > {C}]",
        "edge": "    return [i for i, x in enumerate(nums) if x >= {C}]",
        "plain": "    return [x for x in nums if x > {C}]",
        "ex": lambda c: [[c - 3, c + 7, c + 1], [c + 2, c - 1]],
        "hid": lambda c: [[], [c], [c, c + 1, c], [c - 1], [c + 3, c, c - 4, c + 9]],
        "level": 1,
    },
    {
        "fn": "shift_letters",
        "sig": "def shift_letters(s: str) -> str:",
        "doc": "Shift each lowercase letter in s forward by {C} places in the alphabet, wrapping from z to a. Leave every other character unchanged.",
        "cs": [1, 2, 3, 4, 5],
        "ref": "    return ''.join(chr((ord(ch) - 97 + {C}) % 26 + 97) if 'a' <= ch <= 'z' else ch for ch in s)",
        "edge": "    return ''.join(chr(ord(ch) + {C}) if 'a' <= ch <= 'z' else ch for ch in s)",
        "plain": "    return ''.join(chr((ord(ch) - 97 - {C}) % 26 + 97) if 'a' <= ch <= 'z' else ch for ch in s)",
        "ex": lambda c: ["abc", "hi there"],
        "hid": lambda c: ["", "xyz", "zebra", "A-z!", "mno"],
        "level": 2,
    },
    {
        "fn": "average_rounded",
        "sig": "def average_rounded(nums: list[float]) -> float:",
        "doc": "Return the average of nums rounded to {C} decimal places, or 0.0 when nums is empty.",
        "cs": [0, 1, 2, 3, 4],
        "ref": "    return round(sum(nums) / len(nums), {C}) if nums else 0.0",
        "edge": "    return round(sum(nums) / len(nums), {C})",
        "plain": "    return sum(nums) / len(nums) if nums else 0.0",
        "ex": lambda c: [[1, 2, 2], [10, 20, 31]],
        "hid": lambda c: [[], [5], [1, 1, 2], [-3, 4], [0.5, 0.25, 0.125]],
        "level": 1,
    },
    {
        "fn": "is_letter_palindrome",
        "sig": "def is_letter_palindrome(s: str) -> bool:",
        "doc": "Return True if s reads the same forwards and backwards after you drop every character that is not a letter and ignore case. Strings with fewer than {C} letters return False.",
        "cs": [1, 2, 3, 4, 5],
        "ref": "    t = [ch.lower() for ch in s if ch.isalpha()]\n    return len(t) >= {C} and t == t[::-1]",
        "edge": "    t = [ch.lower() for ch in s if ch != ' ']\n    return len(t) >= {C} and t == t[::-1]",
        "plain": "    t = [ch for ch in s if ch.isalpha()]\n    return len(t) >= {C} and t == t[::-1]",
        "ex": lambda c: ["Level", "hello"],
        "hid": lambda c: ["A man, a plan, a canal: Panama", "", "No 'x' in Nixon", "ab", "Was it a car?"],
        "level": 3,
    },
    {
        "fn": "keep_at_most",
        "sig": "def keep_at_most(items: list[int]) -> list[int]:",
        "doc": "Return items with each value kept at most {C} times, in the original order.",
        "cs": [1, 2, 3, 4, 5],
        "ref": "    seen: dict = {}\n    out = []\n    for x in items:\n        if seen.get(x, 0) < {C}:\n            out.append(x)\n            seen[x] = seen.get(x, 0) + 1\n    return out",
        "edge": "    seen: dict = {}\n    out = []\n    for x in sorted(items):\n        if seen.get(x, 0) < {C}:\n            out.append(x)\n            seen[x] = seen.get(x, 0) + 1\n    return out",
        "plain": "    seen: dict = {}\n    out = []\n    for x in items:\n        if seen.get(x, 0) <= {C}:\n            out.append(x)\n            seen[x] = seen.get(x, 0) + 1\n    return out",
        "ex": lambda c: [[1] * (c + 2) + [2], [3, 4, 5]],
        "hid": lambda c: [[], [9, 1] * (c + 1), [5, 3, 5, 3, 1], [2] * c, [4, 2, 4] * 2],
        "level": 3,
    },
]


def _src(t: dict, which: str, c: int) -> str:
    return t["sig"] + "\n" + t[which].replace("{C}", str(c)) + "\n"


def _call(src: str, fn: str, arg):
    ns: dict = {}
    exec(src, ns)  # noqa: S102 - generator runs its own fixed reference code
    try:
        return ns[fn](arg)
    except Exception as e:  # noqa: BLE001
        return f"error:{type(e).__name__}"


def _asserts(fn: str, ref: str, args: list) -> list[str]:
    return [f"assert {fn}({a!r}) == {_call(ref, fn, a)!r}" for a in args]


def _passes(src: str, fn: str, ref: str, args: list) -> bool:
    return all(_call(src, fn, a) == _call(ref, fn, a) for a in args)


def _code_task(t: dict, c: int) -> tuple[str, dict, dict]:
    ref, edge, plain = (_src(t, w, c) for w in ("ref", "edge", "plain"))
    ex, hid = t["ex"](c), t["hid"](c)
    if not (_passes(edge, t["fn"], ref, ex) and not _passes(edge, t["fn"], ref, hid)):
        raise ValueError(f"{t['fn']} c={c}: the edge body must pass the examples and fail a hidden test")
    if _passes(plain, t["fn"], ref, ex):
        raise ValueError(f"{t['fn']} c={c}: the plain body must fail an example")
    doc = t["doc"].replace("{C}", str(c))
    examples = _asserts(t["fn"], ref, ex)
    prompt = (
        f'Write this Python function.\n\n{t["sig"]}\n    """{doc}"""\n\n'
        "These example tests must pass:\n" + "\n".join(examples)
    )
    visible = {"kind": "code", "function": t["fn"], "example_tests": examples, "level": t["level"]}
    hidden = {"hidden_tests": _asserts(t["fn"], ref, hid)}
    world = {"correct": [ref], "visible_fail": [plain], "hidden_fail": [edge]}
    return prompt, visible | {"_hidden": hidden}, world


# ---------------------------------------------------------------- build


def build() -> tuple[list[dict], list[dict], list[dict], dict]:
    rng = random.Random(SEED)  # noqa: S311 - seeded on purpose, so the task set is reproducible
    vis, hid, world = [], [], []
    for i in range(60):
        text, gold, steps = _math(rng, i % 10)
        tid = f"math-{i:03d}"
        vis.append({"id": tid, "family": "math", "prompt": text, "visible": {"kind": "number", "steps": steps}})
        hid.append({"id": tid, "gold": gold})
        wrongs = _math_wrongs(rng, gold)
        world.append({"id": tid, "correct": [str(gold)], "visible_fail": wrongs[3:], "hidden_fail": wrongs[:3]})
    kinds = list(SCHEMAS)
    for i in range(60):
        kind = kinds[i % len(kinds)]
        text, gold, noise = _json_task(rng, kind)
        tid = f"json-{i:03d}"
        schema = SCHEMAS[kind]
        prompt = (
            "Extract these fields from the text and answer with one JSON object only.\n"
            f"Fields and types: {json.dumps(schema)}\n\nText: {text}"
        )
        vis.append(
            {
                "id": tid,
                "family": "json",
                "prompt": prompt,
                "visible": {"kind": "json", "schema": schema, "distractors": noise},
            }
        )
        hid.append({"id": tid, "gold": gold})
        invalid, wrong = _json_wrongs(rng, gold, schema)
        world.append({"id": tid, "correct": [json.dumps(gold)], "visible_fail": invalid, "hidden_fail": wrong})
    i = 0
    for t in CODE:
        for c in t["cs"]:
            prompt, visible, w = _code_task(t, c)
            tid = f"code-{i:03d}"
            hidden = visible.pop("_hidden")
            vis.append({"id": tid, "family": "code", "prompt": prompt, "visible": visible})
            hid.append({"id": tid} | hidden)
            world.append({"id": tid} | w)
            i += 1
    split = make_split([v["id"] for v in vis])
    return vis, hid, world, split


def make_split(ids: list[str], seed: int = SEED) -> dict:
    """60% development, 40% held out, stratified by family, fixed before any tuning."""
    dev, held = [], []
    for fam in ("math", "json", "code"):
        group = sorted(x for x in ids if x.startswith(fam))
        random.Random(f"{seed}-{fam}").shuffle(group)  # noqa: S311 - seeded split, not security
        cut = round(len(group) * 0.6)
        dev += sorted(group[:cut])
        held += sorted(group[cut:])
    return {"seed": seed, "rule": "60% dev, 40% held out, stratified by family", "dev": dev, "heldout": held}


def _jsonl(rows: list[dict]) -> str:
    return "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows)


def render() -> dict[str, str]:
    vis, hid, world, split = build()
    return {
        "tasks/visible.jsonl": _jsonl(vis),
        "tasks/hidden.jsonl": _jsonl(hid),
        "tasks/split.json": json.dumps(split, indent=1, sort_keys=True) + "\n",
        "fake/world.jsonl": _jsonl(world),
    }


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def write(data_dir: Path) -> dict[str, str]:
    files = render()
    for rel, text in files.items():
        p = data_dir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return {rel: sha(text) for rel, text in files.items()}
