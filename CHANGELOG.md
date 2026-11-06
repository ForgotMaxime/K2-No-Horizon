# Changelog

Tous les changements notables de K2-No-Horizon sont documentés ici.
Format basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/).

## [Unreleased]

- Guider le format des réponses (exemple d’en-têtes de diff, rappel `path:function`) sans donner les réponses ; grouper les changements de harnais avant `reset` + re-mesure.
- Étendre la suite : patches sur `tax.py`/`cache.py`/`auth.py`, navigation multi-sauts.

## [0.4.0] - 2026-11-06

### Ajouté

- 4 tâches agentic (12 au total) : nav-3 (`discount:apply_discount`), nav-4 (`order_reader:get_order`), debug-3 (`pagination`, offset `(page - 1) * size`), patch-5 (`discount`, opérateur `discount-apply`), avec `src/discount.py`, `src/pagination.py`, `tests/test_discount.py`.
- `benchmark/codegen.json` : 24 tâches de complétion de fonctions style LiveCodeBench, tests cachés exécutés en processus isolé (`run_codegen_tests`, timeout 15 s).
- `SUITE_FILES` couvre les nouveaux fichiers.

## [0.3.0] - 2026-11-06

### Ajouté

- Outils `SIGS:` (signatures AST par fichier, sans lecture complète) et `GREP:` (recherche de mot-clé `fichier:ligne:texte`, max 30) avec trace ; guide d'outils « start cheap ».
- `harness/mutate.py` : 4 opérateurs d'injection de bugs (`pricing-tax`, `tags-strip`, `tax-double`, `auth-eq`) avec aller-retour rouge-avant/vert-après testé.

## [0.2.0] - 2026-11-06

### Ajouté

- Suite `k2-no-horizon-v2` : 8 tâches (2 navigation, 2 diagnostic, 4 patch). Nouveau : patch-3 (`src/pricing/tax.py`, cause racine de nav-1) et patch-4 (`src/auth.py`, comparaison par valeur).
- `tests/test_auth.py` : rouge avant patch (chaînes non internées via `"".join`), vert après.
- `SUITE_FILES` inclut le nouveau test.

## [0.1.0] - 2026-11-06

### Ajouté

- Mini-dépôt multi-fichiers : `pricing.py` (bug `add_tax`), `tags.py` (bug `parse_tags`), `src/cart.py`, `src/pricing/tax.py` (double taxe), `src/cache.py` (test `None`), `src/auth.py` (`is` vs `==`), `src/api.py` (distracteur), arbre `app/routes|services|storage|models`.
- `benchmark/tasks.json` : suite `k2-no-horizon-v1`, 6 tâches (2 navigation, 2 diagnostic, 2 patch) avec `required_tools` et `max_steps` 6.
- `harness/tools.py` : `RepoSandbox` (`list_files` / `read_file` / `apply_patch`, `pytest` isolé sur copie temp, anti-traversal, trace des appels). Sans dépendance torch/GPU.
- `harness/grade.py` : grading strict (chemin exact, diff mono-fichier applicable, AST restreint, `tools_ok`), `suite_identity` SHA-256 sur tâches + sources + tests.
- `harness/test_harness.py` : 10 tests CPU (sandbox, diffs, grading, identité de suite, pytest isolé rouge-avant/vert-après).
- `tests/` : `test_pricing.py`, `test_tags.py`, `test_tax.py` (rouges avant patch, attendus), `test_order_store.py` (vert).
- `pyproject.toml`, `README.md`, `.gitignore`.

### Vérifié

- `python -m unittest harness.test_harness -v` : 10/10 OK.
- `python -m pytest -q` : 3 échecs attendus (`pricing`, `tags`, `tax`), 1 succès (`order_store`).
- Branché au moteur ENDP le 2026-11-06 : baseline **26/36** (12 agentic + 24 codegen ; codegen 22/24, seuls `cg-lcm` et `cg-valid-parens` ratent). Leçon v3/v4 : exemples d'outils concrets copiés tels quels (0/8) → exemples abstraits.
