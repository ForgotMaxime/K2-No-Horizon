"""Build benchmark/guardrail.json: ~30 prompts courts d'instruction-following.

Chaque item suit le schema simple::

    {"id": str, "prompt": str, "checks": [{"type": ..., ...}]}

Les ``checks`` sont evalues par ``harness/guardrail.py::run_guardrail_tests``
(pur Python, aucune dependance modele). Contraintes couvertes : phrases
exactes, items numerotes, suffixe/prefixe, mot interdit, mot-clCle requis,
majuscules/minuscules, bornes de mots. Quelques items combinent 2 checks.

Usage (CPU uniquement, stdlib)::

    python benchmark/build_guardrail.py   # regenere guardrail.json (~30 items)

Volontairement NON integre a la suite active (grade.py SUITE_FILES intact :
pas de reset moteur).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "guardrail.json"


def _items() -> list[dict]:
    return [
        {"id": "g-01-exact-2-sent",
         "prompt": "Explique ce qu'est une API. Reponds en exactement 2 phrases.",
         "checks": [{"type": "sentences", "exact": 2}]},
        {"id": "g-02-three-numbered",
         "prompt": "Cite 3 fruits, un par ligne, numerotes comme '1. ...', '2. ...', '3. ...'.",
         "checks": [{"type": "numbered_items", "exact": 3}]},
        {"id": "g-03-suffix-bravo",
         "prompt": "Resume la photosynthese en une phrase. Termine ta reponse par le mot BRAVO.",
         "checks": [{"type": "suffix", "text": "BRAVO"}]},
        {"id": "g-04-no-bananas",
         "prompt": "Decris un petit-dejeuner equilibre. N'utilise jamais le mot 'banane'.",
         "checks": [{"type": "forbidden", "word": "banane"}]},
        {"id": "g-05-uppercase",
         "prompt": "Reponds en majuscules uniquement : dis bonjour au soleil.",
         "checks": [{"type": "uppercase"}]},
        {"id": "g-06-lowercase",
         "prompt": "reponds en minuscules uniquement : presente ton plat prefere",
         "checks": [{"type": "lowercase"}]},
        {"id": "g-07-prefix-voici",
         "prompt": "Commence ta reponse par le mot 'Voici' puis definis la gravite.",
         "checks": [{"type": "prefix", "text": "Voici"}]},
        {"id": "g-08-keyword-loutre",
         "prompt": "Parle des rivieres. Ta reponse doit contenir le mot 'loutre'.",
         "checks": [{"type": "keyword", "keyword": "loutre"}]},
        {"id": "g-09-max-20-words",
         "prompt": "Resume le velo en 20 mots maximum.",
         "checks": [{"type": "word_count", "max": 20}]},
        {"id": "g-10-min-30-words",
         "prompt": "Raconte une promenade en foret en au moins 30 mots.",
         "checks": [{"type": "word_count", "min": 30}]},
        {"id": "g-11-exact-1-sent",
         "prompt": "Definis l'oxymore en exactement 1 phrase.",
         "checks": [{"type": "sentences", "exact": 1}]},
        {"id": "g-12-two-numbered",
         "prompt": "Donne 2 capitales europeennes, numerotees '1. ...' et '2. ...'.",
         "checks": [{"type": "numbered_items", "exact": 2}]},
        {"id": "g-13-suffix-merci",
         "prompt": "Remercie ton lecteur en une phrase et termine par le mot 'merci'.",
         "checks": [{"type": "suffix", "text": "merci"}]},
        {"id": "g-14-no-soleil",
         "prompt": "Decris la nuit etoilee sans utiliser le mot 'soleil'.",
         "checks": [{"type": "forbidden", "word": "soleil"}]},
        {"id": "g-15-upper-keyword",
         "prompt": "EN MAJUSCULES : ecris une phrase contenant le mot LUNE.",
         "checks": [{"type": "uppercase"}, {"type": "keyword", "keyword": "LUNE"}]},
        {"id": "g-16-lower-suffix",
         "prompt": "en minuscules : ecris une phrase qui se termine par le mot 'fin'",
         "checks": [{"type": "lowercase"}, {"type": "suffix", "text": "fin"}]},
        {"id": "g-17-max-10-words-kw",
         "prompt": "En 10 mots maximum, ecris une phrase contenant le mot 'radar'.",
         "checks": [{"type": "word_count", "max": 10}, {"type": "keyword", "keyword": "radar"}]},
        {"id": "g-18-four-numbered",
         "prompt": "Liste 4 saisons, une par ligne, numerotees '1. ...' a '4. ...'.",
         "checks": [{"type": "numbered_items", "exact": 4}]},
        {"id": "g-19-exact-3-sent",
         "prompt": "Presente ton animal prefere en exactement 3 phrases.",
         "checks": [{"type": "sentences", "exact": 3}]},
        {"id": "g-20-prefix-il-etait",
         "prompt": "Commence par 'Il etait' puis raconte une micro-histoire en une phrase.",
         "checks": [{"type": "prefix", "text": "Il etait"}]},
        {"id": "g-21-no-pluie-kw",
         "prompt": "Parle du desert : inclut le mot 'sable' mais jamais le mot 'pluie'.",
         "checks": [{"type": "keyword", "keyword": "sable"}, {"type": "forbidden", "word": "pluie"}]},
        {"id": "g-22-min-2-sent",
         "prompt": "Explique le tri a bulles en au moins 2 phrases.",
         "checks": [{"type": "sentences", "min": 2}]},
        {"id": "g-23-max-3-sent",
         "prompt": "Resume la revolution francaise en 3 phrases maximum.",
         "checks": [{"type": "sentences", "max": 3}]},
        {"id": "g-24-suffix-point",
         "prompt": "Dis au revoir en une phrase qui termine par un point d'exclamation.",
         "checks": [{"type": "suffix", "text": "!"}]},
        {"id": "g-25-five-numbered",
         "prompt": "Cite 5 couleurs, une par ligne, numerotees '1. ...' a '5. ...'.",
         "checks": [{"type": "numbered_items", "exact": 5}]},
        {"id": "g-26-upper-suffix",
         "prompt": "EN MAJUSCULES : encourage un coureur et termine par le mot VICTOIRE.",
         "checks": [{"type": "uppercase"}, {"type": "suffix", "text": "VICTOIRE"}]},
        {"id": "g-27-exact-range-words",
         "prompt": "Decris un phare en 15 mots au minimum et 25 mots au maximum.",
         "checks": [{"type": "word_count", "min": 15, "max": 25}]},
        {"id": "g-28-no-voiture-kw-train",
         "prompt": "Compare deux transports : inclut le mot 'train' mais jamais le mot 'voiture'.",
         "checks": [{"type": "keyword", "keyword": "train"}, {"type": "forbidden", "word": "voiture"}]},
        {"id": "g-29-prefix-liste-suffix",
         "prompt": "Commence par 'Liste :' puis cite 2 outils numerotes '1. ...' et '2. ...'.",
         "checks": [{"type": "prefix", "text": "Liste :"}, {"type": "numbered_items", "exact": 2}]},
        {"id": "g-30-exact-2-sent-kw",
         "prompt": "En exactement 2 phrases contenant le mot 'horloge', explique l'heure d'ete.",
         "checks": [{"type": "sentences", "exact": 2}, {"type": "keyword", "keyword": "horloge"}]},
    ]


def main() -> int:
    tasks = _items()
    ids = [t["id"] for t in tasks]
    assert len(tasks) == 30, f"attendu 30 items, trouve {len(tasks)}"
    assert len(set(ids)) == len(ids), "ids dupliques"
    for t in tasks:
        assert set(t) == {"id", "prompt", "checks"}, f"schema invalide: {t['id']}"
        assert isinstance(t["checks"], list) and t["checks"], t["id"]
    OUT.write_text(
        json.dumps({"suite": "guardrail", "max_retries": 0, "tasks": tasks},
                   ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    print(f"wrote {len(tasks)} tasks to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
