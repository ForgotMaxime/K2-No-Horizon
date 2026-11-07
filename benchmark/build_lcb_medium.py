"""Build benchmark/livecodebench_medium.json: LCB medium slice (stdin/stdout, hidden tests).

Same pattern as build_livecodebench.py (easy slice): downloads
test*.jsonl from livecodebench/code_generation_lite via HF Hub (uses the
same local cache — no new download expected), keeps difficulty ==
'medium', decodes private tests (base64 pickled list), caps cases per
problem at MAX_CASES and total tasks at MAX_TASKS. Reproducible: same
inputs -> same JSON.

Output schema matches livecodebench.json: each task has
id / prompt / starter / tests[{input, output}] / difficulty / platform.
IDs use the distinct prefix 'lcb-medium-' (easy slice uses 'lcb-').

Not wired into the active suite (grade.py SUITE_FILES untouched):
emit livecodebench_medium.json next to livecodebench.json only.
"""
from __future__ import annotations

import base64
import json
import pickle
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "livecodebench_medium.json"
MAX_CASES = 4  # 1 public + up to 3 private (same as easy slice)
MAX_TASKS = 150  # medium stdin pool is ~175; keep 120-150 slice
DIFFICULTY = "medium"
ID_PREFIX = "lcb-medium"


def load_all() -> list:
    from huggingface_hub import snapshot_download

    root = Path(snapshot_download("livecodebench/code_generation_lite", repo_type="dataset"))
    recs = []
    for f in sorted((root).glob("test*.jsonl")):
        recs.extend(json.loads(line) for line in f.read_text(encoding="utf-8").splitlines() if line.strip())
    return recs


def decode_private(blob: str) -> list:
    import pickle
    import zlib

    return pickle.loads(zlib.decompress(base64.b64decode(blob)))


def as_cases(value) -> list:
    if isinstance(value, str):
        value = json.loads(value)
    return value if isinstance(value, list) else []


def convert(rec: dict, idx: int) -> dict:
    cases = []
    for case in as_cases(rec.get("public_test_cases", [])) + as_cases(decode_private(rec["private_test_cases"])):
        if not isinstance(case, dict) or case.get("testtype", "stdin") != "stdin":
            continue
        cases.append({"input": case["input"], "output": case["output"]})
        if len(cases) >= MAX_CASES:
            break
    prompt = rec["question_content"].strip()
    prompt += "\n\nWrite a complete Python program that reads from standard input and writes the answer to standard output. Reply with Python code only, no explanation."
    return {
        "id": f"{ID_PREFIX}-{rec.get('platform', 'x')}-{rec.get('question_id', idx)}",
        "prompt": prompt,
        "starter": "",
        "tests": cases,
        "difficulty": rec.get("difficulty", DIFFICULTY),
        "platform": rec.get("platform", "?"),
    }


def main() -> None:
    recs = [r for r in load_all() if r.get("difficulty") == DIFFICULTY]
    io_tasks = []
    for i, r in enumerate(recs):
        kinds = {c.get("testtype") for c in as_cases(r.get("public_test_cases", []))}
        # Same routing as the easy builder: stdin (or unknown) -> io task.
        # Functional (leetcode-style) records are out of scope for this slice.
        if "stdin" in kinds or not kinds:
            t = convert(r, i)
            if t["tests"]:
                io_tasks.append(t)
        if len(io_tasks) >= MAX_TASKS:
            break
    OUT.write_text(json.dumps({"suite": "lcb-medium", "max_retries": 1, "tasks": io_tasks}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {len(io_tasks)} io tasks to {OUT}")


if __name__ == "__main__":
    sys.exit(main())
