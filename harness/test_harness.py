"""CPU checks for the tool sandbox and strict grading (no model, no GPU)."""
from __future__ import annotations

import unittest
from pathlib import Path

from harness.grade import (
    apply_single_file_diff,
    grade_debug,
    grade_nav,
    grade_patch,
    safe_function_tests,
    suite_identity,
)
from harness.tools import RepoSandbox

ROOT = Path(__file__).resolve().parents[1]

PRICING_DIFF = """diff --git a/pricing.py b/pricing.py
--- a/pricing.py
+++ b/pricing.py
@@ -1,2 +1,2 @@
 def add_tax(price, rate):
-    return price * rate
+    return price * (1 + rate)
"""


class SandboxTests(unittest.TestCase):
    def test_list_files_finds_nav_targets(self):
        box = RepoSandbox(ROOT)
        files = box.list_files()
        for expected in ("pricing.py", "tags.py", "src/pricing/tax.py", "app/storage/order_store.py"):
            self.assertIn(expected, files)

    def test_read_file_returns_buggy_content_and_blocks_traversal(self):
        box = RepoSandbox(ROOT)
        self.assertIn("price * rate", box.read_file("pricing.py"))
        with self.assertRaises(ValueError):
            box.read_file("../handoff.md")

    def test_isolated_pytest_red_before_green_after(self):
        box = RepoSandbox(ROOT)
        self.assertNotEqual(box.run_pytest_isolated("tests/test_pricing.py"), 0)
        fixed = "def add_tax(price, rate):\n    return price * (1 + rate)\n"
        self.assertEqual(box.run_pytest_isolated("tests/test_pricing.py", {"pricing.py": fixed}), 0)


class DiffTests(unittest.TestCase):
    def test_accepts_correct_single_file_diff(self):
        updated, ok = apply_single_file_diff("def add_tax(price, rate):\n    return price * rate\n", PRICING_DIFF, "pricing.py")
        self.assertTrue(ok)
        self.assertTrue(safe_function_tests(updated, "add_tax", [(100, 0.2)], [120]))

    def test_rejects_wrong_path_and_multi_file(self):
        other = PRICING_DIFF.replace("pricing.py", "other.py")
        _, ok = apply_single_file_diff("x\n", other, "pricing.py")
        self.assertFalse(ok)
        multi = PRICING_DIFF + "diff --git a/other.py b/other.py\n"
        _, ok = apply_single_file_diff("x\n", multi, "pricing.py")
        self.assertFalse(ok)

    def test_rejects_disallowed_ast(self):
        self.assertFalse(safe_function_tests("import os\ndef add_tax(x, y):\n    return x + y\n", "add_tax", [(1, 2)], [3]))


class GradingTests(unittest.TestCase):
    def test_nav_requires_exact_path_and_tool_trace(self):
        task = {"answer_path": "src/pricing/tax.py", "answer_function": "calculate_total", "required_tools": ["list_files", "read_file"]}
        self.assertTrue(grade_nav("src/pricing/tax.py:calculate_total", task, ["list_files", "read_file:src/cart.py"]))
        self.assertFalse(grade_nav("src/pricing/tax.py:calculate_total", task, ["read_file:src/cart.py"]))
        self.assertFalse(grade_nav("src/cart.py:checkout", task, ["list_files", "read_file:src/cart.py"]))

    def test_debug_requires_needles_and_read(self):
        task = {"needles": ["if key not in cache"], "required_tools": ["read_file"]}
        self.assertTrue(grade_debug("if key not in cache:", task, ["read_file:src/cache.py"]))
        self.assertFalse(grade_debug("if key not in cache:", task, []))

    def test_patch_requires_path_tests_and_read(self):
        task = {"target_file": "pricing.py", "function": "add_tax", "test_args": [[100, 0.2]], "test_expected": [120], "required_tools": ["read_file"]}
        original = "def add_tax(price, rate):\n    return price * rate\n"
        good = grade_patch("```diff\n" + PRICING_DIFF + "```", task, ["read_file:pricing.py"], original)
        self.assertTrue(good["pass"])
        bad_trace = grade_patch("```diff\n" + PRICING_DIFF + "```", task, [], original)
        self.assertFalse(bad_trace["pass"])
        wrong = grade_patch("no diff here", task, ["read_file:pricing.py"], original)
        self.assertFalse(wrong["pass"])

    def test_suite_identity_stable(self):
        self.assertEqual(suite_identity(ROOT), suite_identity(ROOT))
        self.assertEqual(len(suite_identity(ROOT)), 64)


if __name__ == "__main__":
    unittest.main()
