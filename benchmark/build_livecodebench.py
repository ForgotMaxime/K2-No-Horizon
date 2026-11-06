"""Build benchmark/livecodebench.json: LCB easy slice (stdin/stdout, hidden tests).

Downloads test*.jsonl from livecodebench/code_generation_lite via HF Hub,
keeps difficulty == 'easy', decodes private tests (base64 pickled list),
caps cases per problem. Reproducible: same inputs -> same JSON.
"""
from __future__ import annotations

import base64
import glob
import json
import pickle
import re
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "livecodebench.json"
OUT_LEETCODE = HERE / "leetcode.json"
MAX_CASES = 4  # 1 public + up to 3 private


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


def parse_expected(text: str):
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return text


def convert_functional(rec: dict, idx: int) -> dict | None:
    starter = rec.get("starter_code", "") or ""
    m_cls = re.search(r"class\s+(\w+)", starter)
    m_fn = re.search(r"def\s+(\w+)\s*\(\s*self", starter)
    if not m_cls or not m_fn:
        return None
    cls_name, fn_name = m_cls.group(1), m_fn.group(1)
    blocks = []
    cases = as_cases(rec.get("public_test_cases", [])) + as_cases(decode_private(rec["private_test_cases"]))
    for i, case in enumerate(cases):
        if not isinstance(case, dict) or case.get("testtype") != "functional":
            continue
        try:
            arg = json.loads(case["input"])
        except (json.JSONDecodeError, ValueError):
            continue
        expected = parse_expected(case["output"])
        # All easy tasks are single-parameter: pass the whole input as the one argument.
        blocks.append(f"_r{i} = {cls_name}().{fn_name}({arg!r})\nassert _r{i} == {expected!r}")
        if len(blocks) >= MAX_CASES:
            break
    if not blocks:
        return None
    prompt = rec["question_content"].strip()
    prompt += f"\n\nComplete the `{cls_name}` class below. Reply with Python code only, no explanation."
    return {
        "id": f"lcb-{rec.get('platform', 'x')}-{rec.get('question_id', idx)}",
        "prompt": prompt,
        "starter": starter,
        "function": f"{cls_name}.{fn_name}",
        "tests": blocks,
    }


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
        "id": f"lcb-{rec.get('platform', 'x')}-{rec.get('question_id', idx)}",
        "prompt": prompt,
        "starter": "",
        "tests": cases,
        "difficulty": rec.get("difficulty", "easy"),
        "platform": rec.get("platform", "?"),
    }


def main() -> None:
    recs = [r for r in load_all() if r.get("difficulty") == "easy"]
    io_tasks, fn_tasks = [], []
    for i, r in enumerate(recs):
        kinds = {c.get("testtype") for c in as_cases(r.get("public_test_cases", []))}
        if "stdin" in kinds or not kinds:
            t = convert(r, i)
            if t["tests"]:
                io_tasks.append(t)
        else:
            t = convert_functional(r, i)
            if t is not None:
                fn_tasks.append(t)
    OUT.write_text(json.dumps({"suite": "lcb-easy", "max_retries": 1, "tasks": io_tasks}, ensure_ascii=False, indent=1), encoding="utf-8")
    OUT_LEETCODE.write_text(json.dumps({"suite": "lcb-leetcode-easy", "max_retries": 1, "tasks": fn_tasks}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {len(io_tasks)} io tasks to {OUT}, {len(fn_tasks)} functional tasks to {OUT_LEETCODE}")


if __name__ == "__main__":
    sys.exit(main())
