"""Tool loop sandbox: list_files / read_file / sigs / grep / apply_patch with trace logging.

Torch-free so `python -m unittest harness.test_harness` runs on CPU.
Isolated pytest runs on a temp copy of the repo, never on the working tree.
"""
from __future__ import annotations

import ast
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SKIP_DIRS = {".git", "__pycache__", ".hf-home", ".pytest_cache", "results"}
GREP_LIMIT = 30


def _is_allowed(path: Path) -> bool:
    if path.suffix != ".py":
        return False
    return not any(part in SKIP_DIRS for part in path.parts)


class RepoSandbox:
    """Operates on a repo snapshot; logs every tool call for grading."""

    def __init__(self, root: Path | str = ROOT):
        self.root = Path(root).resolve()
        self.trace: list[str] = []

    def list_files(self) -> list[str]:
        self.trace.append("list_files")
        out = []
        for path in sorted(self.root.rglob("*.py")):
            rel = path.relative_to(self.root)
            if _is_allowed(rel):
                out.append(rel.as_posix())
        return out

    def _load(self, relpath: str) -> str:
        target = (self.root / relpath).resolve()
        if not str(target).startswith(str(self.root)):
            raise ValueError(f"path traversal blocked: {relpath}")
        if not target.is_file():
            raise FileNotFoundError(relpath)
        return target.read_text(encoding="utf-8")

    def read_file(self, relpath: str) -> str:
        self.trace.append(f"read_file:{relpath}")
        return self._load(relpath)

    def sigs(self, relpath: str) -> list[str]:
        """List top-level function/class signatures with line numbers (no full read)."""
        self.trace.append(f"sigs:{relpath}")
        try:
            tree = ast.parse(self._load(relpath))
        except (SyntaxError, ValueError, FileNotFoundError) as exc:
            return [f"<parse-error: {exc}>"]
        out = []
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = [a.arg for a in node.args.args]
                out.append(f"L{node.lineno} def {node.name}({', '.join(args)})")
            elif isinstance(node, ast.ClassDef):
                out.append(f"L{node.lineno} class {node.name}")
        return out or ["<no top-level defs>"]

    def grep(self, pattern: str, limit: int = GREP_LIMIT) -> list[str]:
        """Case-insensitive keyword search over repo .py files: file:line:text."""
        self.trace.append(f"grep:{pattern}")
        needle = pattern.casefold()
        hits = []
        for path in sorted(self.root.rglob("*.py")):
            rel = path.relative_to(self.root)
            if not _is_allowed(rel) or len(hits) >= limit:
                break
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except OSError:
                continue
            for i, line in enumerate(lines):
                if needle in line.casefold():
                    hits.append(f"{rel.as_posix()}:{i + 1}:{line.strip()[:120]}")
                    if len(hits) >= limit:
                        break
        return hits or ["<no matches>"]

    def apply_patch(self, patch: str, expected_path: str):
        """Apply a single-file unified diff to the file content in the snapshot."""
        self.trace.append(f"apply_patch:{expected_path}")
        try:
            original = self.read_file(expected_path)
        except (FileNotFoundError, ValueError):
            return None, False
        from harness.grade import apply_single_file_diff

        return apply_single_file_diff(original, patch, expected_path)

    def run_pytest_isolated(self, test_file: str, patches: dict[str, str] | None = None) -> int:
        """Copy repo to temp dir, optionally apply patched file contents, run pytest.

        patches maps relpath -> full new file content (not diff). Returns exit code.
        """
        self.trace.append(f"pytest:{test_file}")
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "repo"
            shutil.copytree(self.root, dest, ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", ".hf-home", "results"))
            if patches:
                for rel, content in patches.items():
                    target = (dest / rel).resolve()
                    if not str(target).startswith(str(dest.resolve())):
                        raise ValueError(f"path traversal blocked: {rel}")
                    target.write_text(content, encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, "-m", "pytest", test_file, "-q"],
                cwd=dest,
                capture_output=True,
                text=True,
            )
            return completed.returncode


TOOL_GUIDE = """You have five tools. Call them as `TOOL: arg` on its own line:
LIST: list_files
READ: <relative/path.py>
SIGS: <relative/path.py> (signatures only, cheap)
GREP: <keyword> (search code, cheap)
PATCH: <unified diff fenced in ```diff>
Start cheap (SIGS/GREP), then READ only the files you need.
Final answers: navigation tasks reply `path:function` only; debug tasks reply one line; patch tasks reply one unified diff and nothing else."""
