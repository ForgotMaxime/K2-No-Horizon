"""Tool loop sandbox: list_files / read_file / apply_patch with trace logging.

Torch-free so `python -m unittest harness.test_harness` runs on CPU.
Isolated pytest runs on a temp copy of the repo, never on the working tree.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SKIP_DIRS = {".git", "__pycache__", ".hf-home", ".pytest_cache", "results"}


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

    def read_file(self, relpath: str) -> str:
        self.trace.append(f"read_file:{relpath}")
        target = (self.root / relpath).resolve()
        if not str(target).startswith(str(self.root)):
            raise ValueError(f"path traversal blocked: {relpath}")
        if not target.is_file():
            raise FileNotFoundError(relpath)
        return target.read_text(encoding="utf-8")

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


TOOL_GUIDE = """You have three tools. Call them as `TOOL: arg` on its own line:
LIST: list_files
READ: <relative/path.py>
PATCH: <unified diff fenced in ```diff>
Final answers: navigation tasks reply `path:function` only; debug tasks reply one line; patch tasks reply one unified diff and nothing else."""
