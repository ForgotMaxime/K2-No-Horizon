"""Build benchmark/codecontests_easy.json: CodeContests easy slice (stdin/stdout, hidden tests).

Streams deepmind/code_contests (train split) via HF Hub in streaming mode
— never a full snapshot (~35 Go): rows are filtered on the fly and the scan
stops as soon as MAX_TASKS tasks are collected (bounded by MAX_SCAN rows).
Keeps source == CODEFORCES with 0 < cf_rating <= RATING_MAX, concatenates
public + private tests (like the livecodebench slices), caps cases per
problem at MAX_CASES. Reproducible: same stream prefix -> same JSON.

Output schema matches livecodebench.json: each task has
id / prompt / starter / tests[{input, output}] / difficulty / platform
(plus cf_rating / cf_index provenance extras).
IDs use the distinct prefix 'lcb-cc-' (easy LCB slice uses 'lcb-',
medium slice 'lcb-medium-', humaneval 'he-'): no collision with the
existing JSONs (asserted at build time).

Not wired into the active suite (grade.py SUITE_FILES untouched):
emit codecontests_easy.json next to the other benchmarks only.
Only writes the JSON if it stays under MAX_JSON_BYTES (100 Mo),
otherwise leaves the builder + a note.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "codecontests_easy.json"
DATASET = "deepmind/code_contests"
SPLIT = "train"
SOURCE_CODEFORCES = 2  # ClassLabel: UNKNOWN=0, CODECHEF=1, CODEFORCES=2, ...
RATING_MAX = 1000  # Codeforces easiest band (800-1000)
MAX_CASES = 4  # public + private concatenated, then capped (same as LCB slices)
MAX_TASKS = 120  # target ~100-150 easy tasks
MAX_SCAN = 20000  # safety bound: stop scanning even if MAX_TASKS unreached
MAX_JSON_BYTES = 100 * 1024 * 1024  # only emit the JSON if < 100 Mo
ID_PREFIX = "lcb-cc"
NEEDED_COLUMNS = [
    "name",
    "description",
    "public_tests",
    "private_tests",
    "source",
    "cf_contest_id",
    "cf_index",
    "cf_rating",
]
EXISTING_JSONS = [
    "livecodebench.json",
    "livecodebench_medium.json",
    "humaneval.json",
    "codegen.json",
    "leetcode.json",
    "tasks.json",
]


def as_pairs(value) -> list[tuple[str, str]]:
    """Normalize CodeContests tests to [(input, output)].

    Handles both shapes: list of {input, output} dicts (local/batch mode)
    and dict of lists {'input': [...], 'output': [...]} (streaming mode).
    """
    if value is None:
        return []
    if isinstance(value, dict):
        inputs = value.get("input") or []
        outputs = value.get("output") or []
        pairs = []
        for i, o in zip(inputs, outputs):
            pairs.append(("" if i is None else str(i), "" if o is None else str(o)))
        return pairs
    if isinstance(value, list):
        pairs = []
        for case in value:
            if isinstance(case, dict) and case.get("input") is not None and case.get("output") is not None:
                pairs.append((str(case["input"]), str(case["output"])))
        return pairs
    return []


def slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s[:40] or "task"


def make_id(rec: dict, seen: set[str]) -> str:
    cid = rec.get("cf_contest_id") or 0
    idx = re.sub(r"[^A-Za-z0-9]", "", str(rec.get("cf_index") or ""))
    base = f"{ID_PREFIX}-{cid}{idx}" if cid and idx else f"{ID_PREFIX}-{slug(rec.get('name') or '')}"
    cand, k = base, 2
    while cand in seen:
        cand = f"{base}-{k}"
        k += 1
    seen.add(cand)
    return cand


def convert(rec: dict, seen: set[str]) -> dict | None:
    pairs = as_pairs(rec.get("public_tests")) + as_pairs(rec.get("private_tests"))
    # Drop degenerate cases (missing output); keep the rest, cap at MAX_CASES.
    pairs = [(i, o) for i, o in pairs if o is not None and str(o) != ""]
    if not pairs:
        return None
    description = (rec.get("description") or "").strip()
    if not description:
        return None
    cases = [{"input": i, "output": o} for i, o in pairs[:MAX_CASES]]
    prompt = description
    prompt += "\n\nWrite a complete Python program that reads from standard input and writes the answer to standard output. Reply with Python code only, no explanation."
    return {
        "id": make_id(rec, seen),
        "prompt": prompt,
        "starter": "",
        "tests": cases,
        "difficulty": "easy",
        "platform": "codeforces",
        "cf_rating": rec.get("cf_rating"),
        "cf_index": str(rec.get("cf_index") or ""),
    }


def existing_ids() -> set[str]:
    ids: set[str] = set()
    for fname in EXISTING_JSONS:
        p = HERE / fname
        if not p.exists():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        tasks = data.get("tasks", []) if isinstance(data, dict) else []
        for t in tasks:
            if isinstance(t, dict) and t.get("id"):
                ids.add(t["id"])
    return ids


def stream_records():
    from datasets import load_dataset

    ds = load_dataset(DATASET, split=SPLIT, streaming=True)
    try:
        ds = ds.select_columns(NEEDED_COLUMNS)  # skip heavy solution columns
    except Exception:
        pass  # older datasets versions: fall back to full rows
    return ds


def main() -> int:
    try:
        ds = stream_records()
    except Exception as exc:  # Hub inaccessible: document the exact obstacle, stop here
        print(f"ABORT: cannot stream {DATASET}/{SPLIT}: {type(exc).__name__}: {exc}")
        print("Obstacle: Hub inaccessible ou dataset non lisible en streaming ; aucun JSON emis.")
        return 1
    taken_ids = existing_ids()
    seen: set[str] = set()
    tasks: list[dict] = []
    scanned = 0
    try:
        for rec in ds:
            scanned += 1
            if scanned > MAX_SCAN:
                print(f"STOP: MAX_SCAN={MAX_SCAN} reached with {len(tasks)} tasks.")
                break
            if rec.get("source") != SOURCE_CODEFORCES:
                continue
            rating = rec.get("cf_rating") or 0
            if not 0 < rating <= RATING_MAX:
                continue
            t = convert(rec, seen)
            if t is None:
                continue
            if t["id"] in taken_ids:
                continue  # no collision with existing benchmark JSONs
            taken_ids.add(t["id"])
            tasks.append(t)
            if len(tasks) >= MAX_TASKS:
                break
    except Exception as exc:  # mid-stream failure: document, keep going with what we have
        print(f"WARN: stream interrupted after {scanned} rows / {len(tasks)} tasks: {type(exc).__name__}: {exc}")
    if not tasks:
        print(f"ABORT: 0 tasks after scanning {scanned} rows (volume ingeable ou filtre trop strict).")
        return 1
    payload = json.dumps({"suite": "codecontests-easy", "max_retries": 1, "tasks": tasks}, ensure_ascii=False, indent=1)
    size = len(payload.encode("utf-8"))
    print(f"scanned {scanned} rows, kept {len(tasks)} codeforces tasks (rating <= {RATING_MAX}), JSON {size / 1e6:.1f} Mo")
    if size >= MAX_JSON_BYTES:
        print(f"NOTE: {size} bytes >= {MAX_JSON_BYTES} (100 Mo): builder seul, JSON non emis.")
        return 0
    OUT.write_text(payload, encoding="utf-8")
    print(f"wrote {len(tasks)} tasks to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
