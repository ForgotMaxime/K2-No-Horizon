"""Build benchmark/humaneval.json: HumanEval tasks as asserts for run_codegen_tests.

Downloads openai/openai_humaneval via HF Hub (lightweight ~84 Ko parquet),
converts each record's ``test`` column (``def check(candidate): ...``)
into a list of standalone assert/setup statements with ``candidate``
renamed to the record's ``entry_point`` (AST-based, handles multi-line
asserts, imports, and for-loops containing asserts).

Output schema mirrors codegen.json: each task has
id / prompt / starter / function / tests (list of code strings).
``solution = prompt + canonical_solution`` passes ``run_codegen_tests``
in harness/grade.py (grade.py untouched — import it read-only).

Not wired into the active suite (grade.py SUITE_FILES untouched):
emit humaneval.json next to the other benchmarks only.
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "humaneval.json"
DATASET = "openai/openai_humaneval"


class _RenameCandidate(ast.NodeTransformer):
    def __init__(self, entry_point: str) -> None:
        self.entry_point = entry_point

    def visit_Name(self, node: ast.Name):  # noqa: N802
        if node.id == "candidate":
            return ast.copy_location(ast.Name(id=self.entry_point, ctx=node.ctx), node)
        return node


def check_body_to_tests(test_src: str, entry_point: str) -> list[str]:
    """Convert ``def check(candidate)`` body to standalone code strings.

    Keeps Assert statements, imports, and assignments/loops that contain
    asserts (e.g. randomized loop tests); drops assert-free fillers such
    as bare ``print`` expressions. ``candidate`` is renamed to entry_point.
    """
    tree = ast.parse(test_src)
    fn = next(
        (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "check"),
        None,
    )
    if fn is None:
        return []
    out: list[str] = []
    for stmt in fn.body:
        has_assert = any(isinstance(n, ast.Assert) for n in ast.walk(stmt))
        if isinstance(stmt, ast.Expr) and not has_assert:
            continue  # drop assert-free fillers such as bare `print`
        # Keep everything else in order (imports, setup assigns, asserts,
        # loops): loop tests depend on preceding setup statements.
        stmt = _RenameCandidate(entry_point).visit(stmt)
        ast.fix_missing_locations(stmt)
        out.append(ast.unparse(stmt))
    return out


def load_records() -> list[dict]:
    from datasets import load_dataset

    ds = load_dataset(DATASET, split="test")
    return [
        {
            "task_id": r["task_id"],
            "prompt": r["prompt"],
            "canonical_solution": r["canonical_solution"],
            "test": r["test"],
            "entry_point": r["entry_point"],
        }
        for r in ds
    ]


def convert(rec: dict) -> dict | None:
    entry = rec["entry_point"]
    tests = check_body_to_tests(rec["test"], entry)
    if not tests or not any(t.strip().startswith(("assert ", "for ", "while ")) for t in tests):
        return None
    prompt = rec["prompt"]
    return {
        "id": "he-" + rec["task_id"].replace("/", "-").lower(),
        "prompt": prompt,
        "starter": prompt,
        "function": entry,
        "tests": tests,
    }


def main() -> None:
    recs = load_records()
    tasks = []
    for r in recs:
        t = convert(r)
        if t is not None:
            tasks.append(t)
    OUT.write_text(
        json.dumps({"suite": "humaneval", "max_retries": 1, "tasks": tasks}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    print(f"wrote {len(tasks)} tasks to {OUT} from {len(recs)} records")


if __name__ == "__main__":
    sys.exit(main())
