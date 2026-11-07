"""Garde-fou instruction-following (pur Python, aucune dependance modele).

Evalue si une reponse textuelle respecte des contraintes de style verifiables
par mots-cles / comptages / pre Exemple ::

    from harness.guardrail import run_guardrail_tests
    out = run_guardrail_tests("BONJOUR TOUT LE MONDE", [{"type": "uppercase"}])
    assert out["passed"] is True

Types de checks supportes (cles additionnelles entre parentheses) :

- ``keyword`` (keyword, case_sensitive=False) : la reponse contient le mot.
- ``forbidden`` (word, case_sensitive=False) : la reponse ne contient pas le mot
  (match par frontieres de mot, pas sous-chaine).
- ``suffix`` (text, case_sensitive=False) : reponse (strip) se termine par text.
- ``prefix`` (text, case_sensitive=False) : reponse (lstrip) commence par text.
- ``sentences`` (exact= | min= | max=) : nombre de phrases (decoupage ``.!?…``).
- ``numbered_items`` (exact= | min= | max=) : lignes ``1. ... 2. ...`` consecutives.
- ``uppercase`` : toutes les lettres sont en majuscules.
- ``lowercase`` : toutes les lettres sont en minuscules.
- ``word_count`` (exact= | min= | max=) : nombre de mots (split whitespace).

Type inconnu -> check en echec (detail explicite), jamais d'exception.
Volontairement NON integre a harness/grade.py (pas de reset de suite).
"""
from __future__ import annotations

import re

SUPPORTED_TYPES = frozenset({
    "keyword", "forbidden", "suffix", "prefix", "sentences",
    "numbered_items", "uppercase", "lowercase", "word_count",
})

_SENT_SPLIT = re.compile(r"[^.!?…]+[.!?…]+(\s+|$)|[^.!?…]+$")
_NUM_LINE = re.compile(r"^\s*(\d+)[.)]\s+\S")


def _norm(s: str, case_sensitive: bool) -> str:
    return s if case_sensitive else s.casefold()


def _count_sentences(answer: str) -> int:
    parts = [m.group(0).strip() for m in _SENT_SPLIT.finditer(answer.strip())]
    return len([p for p in parts if p])


def _count_numbered_items(answer: str) -> int:
    count, expected = 0, 1
    for line in answer.splitlines():
        m = _NUM_LINE.match(line)
        if m and int(m.group(1)) == expected:
            count += 1
            expected += 1
    return count


def _check_word_count(n: int, spec: dict) -> tuple[bool, str]:
    for key, op in (("exact", "=="), ("min", ">="), ("max", "<=")):
        if key in spec and not _cmp(n, op, int(spec[key])):
            return False, f"word_count={n} viole {key}={spec[key]}"
    return True, f"word_count={n} ok"


def _cmp(n: int, op: str, ref: int) -> bool:
    return {"==": n == ref, ">=": n >= ref, "<=": n <= ref}[op]


def _run_one(answer: str, spec: dict) -> tuple[bool, str]:
    ctype = spec.get("type")
    if ctype not in SUPPORTED_TYPES:
        return False, f"type inconnu: {ctype!r}"
    cs = bool(spec.get("case_sensitive", False))
    text, norm = answer, _norm(answer, cs)

    if ctype == "keyword":
        kw = _norm(str(spec.get("keyword", "")), cs)
        ok = kw != "" and kw in norm
        return ok, f"keyword {spec.get('keyword')!r} {'trouve' if ok else 'absent'}"
    if ctype == "forbidden":
        word = str(spec.get("word", ""))
        pat = re.compile(r"\b" + re.escape(word) + r"\b",
                         0 if cs else re.IGNORECASE)
        ok = word != "" and pat.search(answer) is None
        return ok, f"mot interdit {word!r} {'absent' if ok else 'present'}"
    if ctype == "suffix":
        suffix = _norm(str(spec.get("text", "")), cs)
        ok = suffix != "" and norm.rstrip().endswith(suffix)
        return ok, f"suffix {spec.get('text')!r} {'ok' if ok else 'manquant'}"
    if ctype == "prefix":
        prefix = _norm(str(spec.get("text", "")), cs)
        ok = prefix != "" and norm.lstrip().startswith(prefix)
        return ok, f"prefix {spec.get('text')!r} {'ok' if ok else 'manquant'}"
    if ctype in ("sentences", "numbered_items", "word_count"):
        n = {"sentences": _count_sentences,
             "numbered_items": _count_numbered_items,
             "word_count": lambda a: len(a.split())}[ctype](answer)
        label = {"sentences": "phrases", "numbered_items": "items",
                 "word_count": "mots"}[ctype]
        for key, op in (("exact", "=="), ("min", ">="), ("max", "<=")):
            if key in spec and not _cmp(n, op, int(spec[key])):
                return False, f"{n} {label} viole {key}={spec[key]}"
        if not any(k in spec for k in ("exact", "min", "max")):
            return False, f"{ctype}: aucune borne exact/min/max"
        return True, f"{n} {label} ok"
    if ctype == "uppercase":
        letters = [c for c in answer if c.isalpha()]
        ok = bool(letters) and all(c.isupper() for c in letters)
        return ok, "tout en majuscules" if ok else "minuscules detectees"
    if ctype == "lowercase":  # pragma: no branch
        letters = [c for c in answer if c.isalpha()]
        ok = bool(letters) and all(c.islower() for c in letters)
        return ok, "tout en minuscules" if ok else "majuscules detectees"
    return False, f"type inconnu: {ctype!r}"  # garde-fou mypy


def run_guardrail_tests(answer: str, checks: list[dict]) -> dict:
    """Evalue ``answer`` contre ``checks``. Retour::

        {"passed": bool, "results": [{"index", "type", "passed", "detail"}]}
    """
    if not isinstance(answer, str):
        answer = str(answer)
    results = []
    for i, spec in enumerate(checks or []):
        if not isinstance(spec, dict):
            results.append({"index": i, "type": None,
                            "passed": False, "detail": "check non-dict"})
            continue
        ok, detail = _run_one(answer, spec)
        results.append({"index": i, "type": spec.get("type"),
                        "passed": ok, "detail": detail})
    return {"passed": all(r["passed"] for r in results), "results": results}
