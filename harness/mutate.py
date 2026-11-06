"""Mutation task generator: inject targeted bugs into clean code to build tasks.

Each operator turns a clean snippet into a buggy one (and back). Used to
expand the suite with red-before/green-after cases without hand-writing each
bug. Torch-free; tested by `harness.test_harness.MutatorTests`.
"""
from __future__ import annotations

OPERATORS = [
    {
        "id": "pricing-tax",
        "target": "pricing.py",
        "good": "    return price * (1 + rate)\n",
        "bad": "    return price * rate\n",
    },
    {
        "id": "tags-strip",
        "target": "tags.py",
        "good": "    return [tag.strip() for tag in text.split(',') if tag.strip()]\n",
        "bad": "    return [tag.strip() for tag in text.split(',') if tag]\n",
    },
    {
        "id": "tax-double",
        "target": "src/pricing/tax.py",
        "good": "    return taxed\n",
        "bad": "    return taxed * (1 + tax_rate)\n",
    },
    {
        "id": "auth-eq",
        "target": "src/auth.py",
        "good": "    if user_name == allowed_name:\n",
        "bad": "    if user_name is allowed_name:\n",
    },
]


def apply_operator(source: str, op_id: str) -> str:
    """Inject the bug: clean source -> buggy source. Raises KeyError/ValueError."""
    op = next(o for o in OPERATORS if o["id"] == op_id)
    if op["good"] not in source:
        raise ValueError(f"operator {op_id}: clean snippet not found")
    return source.replace(op["good"], op["bad"], 1)


def remove_operator(source: str, op_id: str) -> str:
    """Apply the fix: buggy source -> clean source. Raises KeyError/ValueError."""
    op = next(o for o in OPERATORS if o["id"] == op_id)
    if op["bad"] not in source:
        raise ValueError(f"operator {op_id}: buggy snippet not found")
    return source.replace(op["bad"], op["good"], 1)


def operator_ids() -> list[str]:
    return [o["id"] for o in OPERATORS]
