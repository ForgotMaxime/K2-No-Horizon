"""Strict grading for K2-No-Horizon: exact paths, applicable diffs, allowlisted tests."""
from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
TASKS_FILE = ROOT / "benchmark" / "tasks.json"

# Files covered by the suite identity hash: tasks + sources + tests.
SUITE_FILES = [
    "benchmark/tasks.json",
    "pricing.py",
    "tags.py",
    "src/cart.py",
    "src/pricing/tax.py",
    "src/cache.py",
    "src/auth.py",
    "tests/test_auth.py",
    "app/routes/orders.py",
    "app/services/order_reader.py",
    "app/storage/order_store.py",
    "app/models/order.py",
    "tests/test_pricing.py",
    "tests/test_tags.py",
    "tests/test_tax.py",
]

SAFE_AST_NODES = {
    ast.Module, ast.FunctionDef, ast.arguments, ast.arg, ast.Return, ast.If,
    ast.Assign, ast.Expr, ast.Name, ast.Load, ast.Store, ast.Constant,
    ast.BinOp, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Compare,
    ast.Eq, ast.NotEq, ast.Lt, ast.Gt, ast.LtE, ast.GtE, ast.BoolOp,
    ast.And, ast.Or, ast.UnaryOp, ast.Not, ast.USub, ast.List, ast.Tuple,
    ast.Dict, ast.ListComp, ast.comprehension, ast.Call, ast.Attribute,
    ast.Subscript, ast.Slice, ast.IfExp,
}
SAFE_METHODS = {"strip", "split", "casefold", "lower", "upper", "replace", "startswith", "endswith"}


def load_tasks():
    return json.loads(TASKS_FILE.read_text(encoding="utf-8"))["tasks"]


def suite_identity(root: Path = ROOT) -> str:
    h = hashlib.sha256()
    for rel in SUITE_FILES:
        data = (root / rel).read_bytes()
        h.update(rel.encode())
        h.update(b"\x00")
        h.update(data)
        h.update(b"\x00")
    return h.hexdigest()


def extract_diff(answer: str) -> str:
    blocks = re.findall(r"```(?:diff)?\s*\n(.*?)```", answer, flags=re.IGNORECASE | re.DOTALL)
    for block in blocks:
        if "diff --git " in block and "@@" in block:
            return block
    # Fallback: raw diff without fences.
    if "diff --git " in answer and "@@" in answer:
        return answer
    return ""


def apply_single_file_diff(source: str, patch: str, expected_path: str):
    if len(re.findall(r"(?m)^diff --git ", patch)) != 1:
        return None, False
    path_match = re.search(r"(?m)^diff --git a/(.*?) b/(.*?)\s*$", patch)
    old_match = re.search(r"(?m)^--- a/(.*?)\s*$", patch)
    new_match = re.search(r"(?m)^\+\+\+ b/(.*?)\s*$", patch)
    if not (path_match and old_match and new_match):
        return None, False
    if path_match.group(1) != expected_path or path_match.group(2) != expected_path:
        return None, False
    if old_match.group(1) != expected_path or new_match.group(1) != expected_path:
        return None, False

    patch_lines = patch.splitlines()
    source_lines = source.splitlines()
    output, cursor, hunk_count = [], 0, 0
    i = 0
    while i < len(patch_lines):
        if not patch_lines[i].startswith("@@ "):
            i += 1
            continue
        hunk_count += 1
        hunk = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", patch_lines[i])
        if not hunk:
            return None, False
        start = int(hunk.group(1)) - 1
        if start < cursor or start > len(source_lines):
            return None, False
        output.extend(source_lines[cursor:start])
        cursor = start
        i += 1
        while i < len(patch_lines) and not patch_lines[i].startswith("@@ "):
            line = patch_lines[i]
            if line.startswith("\\ No newline"):
                i += 1
                continue
            if not line or line[0] not in " +-":
                break
            content = line[1:]
            if line[0] == " ":
                if cursor >= len(source_lines) or source_lines[cursor] != content:
                    return None, False
                output.append(content)
                cursor += 1
            elif line[0] == "-":
                if cursor >= len(source_lines) or source_lines[cursor] != content:
                    return None, False
                cursor += 1
            else:
                output.append(content)
            i += 1
    if not hunk_count:
        return None, False
    output.extend(source_lines[cursor:])
    return "\n".join(output) + ("\n" if source.endswith("\n") else ""), True


def safe_function_tests(source: str, function_name: str, args_list, expected_list) -> bool:
    try:
        tree = ast.parse(source)
        if any(type(node) not in SAFE_AST_NODES for node in ast.walk(tree)):
            return False
        functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
        if function_name not in functions or len(functions) != len(tree.body):
            return False
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr not in SAFE_METHODS:
                return False
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id not in {"min", "max", "len", "abs", "sum"}:
                    return False
                if isinstance(node.func, ast.Attribute) and node.func.attr not in SAFE_METHODS:
                    return False
        scope: dict = {"__builtins__": {"min": min, "max": max, "len": len, "abs": abs, "sum": sum}}
        exec(compile(tree, "<generated-patch>", "exec"), scope, scope)
        return all(scope[function_name](*args) == expected for args, expected in zip(args_list, expected_list))
    except Exception:
        return False


def _tools_ok(trace: list[str], required: list[str]) -> bool:
    kinds = set()
    for entry in trace:
        kinds.add(entry.split(":")[0])
    mapping = {"list_files": "list_files", "read_file": "read_file", "apply_patch": "apply_patch", "pytest": "pytest"}
    return all(mapping.get(r, r) in kinds for r in required)


def grade_nav(answer: str, task: dict, trace: list[str]) -> bool:
    text = answer.casefold()
    ok = task["answer_path"].casefold() in text and task["answer_function"].casefold() in text
    return bool(ok) and _tools_ok(trace, task.get("required_tools", []))


def grade_debug(answer: str, task: dict, trace: list[str]) -> bool:
    text = answer.casefold()
    ok = all(needle.casefold() in text for needle in task["needles"])
    return bool(ok) and _tools_ok(trace, task.get("required_tools", []))


def grade_patch(answer: str, task: dict, trace: list[str], original: str) -> dict:
    diff = extract_diff(answer)
    updated, path_ok = apply_single_file_diff(original, diff, task["target_file"])
    # JSON stores args as lists; call with *args so ["red, ,blue"] -> ("red, ,blue").
    call_args = [tuple(a) if isinstance(a, list) else a for a in task["test_args"]]
    tests_ok = bool(updated is not None and safe_function_tests(updated, task["function"], call_args, task["test_expected"]))
    tools_ok = _tools_ok(trace, task.get("required_tools", []))
    passed = bool(path_ok and tests_ok and tools_ok)
    return {"path_ok": path_ok, "tests_pass": tests_ok, "tools_ok": tools_ok, "pass": passed, "updated": updated}
