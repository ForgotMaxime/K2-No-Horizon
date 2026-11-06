# Changelog

Tous les changements notables de K2-No-Horizon sont documentés ici.
Format basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/).

## [Unreleased]

- Brancher `run_local` v2 (boucle d'outils multi-tours `list/read/apply_patch`) sur cette suite, puis ouvrir une nouvelle comparaison moteur (`reset`) et re-mesurer baseline/candidats.

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
