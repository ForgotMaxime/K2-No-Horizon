# K2-No-Horizon — mini-dépôt benchmark

Mini-projet Python multi-fichiers pour évaluer la navigation, le diagnostic et les patches avec une boucle d'outils `list / read / apply_patch`, puis l'exécution des tests en environnement isolé.

## Arbre

```text
pricing.py                  # patch-1 : bug add_tax (retourne price*rate)
tags.py                     # patch-2 : bug parse_tags (garde les entrées blanches)
src/cart.py                 # appelle calculate_total
src/pricing/tax.py          # nav-1 + patch-3 : taxe appliquée deux fois
src/cache.py                # debug-1 : cache.get(key) is None
src/auth.py                 # debug-2 + patch-4 : `is` au lieu de `==`
src/api.py                  # distracteur
app/routes/orders.py        # appelle order_reader.get_order
app/services/order_reader.py# appelle order_store.fetch
app/storage/order_store.py  # nav-2 : contient le SQL, définit fetch
app/models/order.py         # modèle Order
tests/                      # pytest : 4 tests rouges avant patch (pricing, tags, tax, auth)
benchmark/tasks.json        # 8 tâches : 2 nav, 2 debug, 4 patch
harness/                    # boucle d'outils (list/read/sigs/grep/apply_patch) + grading strict + mutateur + tests CPU
```

## Règle de reprise (même discipline que le moteur WSP)

Aucun candidat n'est une amélioration sans dépasser strictement le meilleur score sur la même suite (`suite_sha256`). Toute modification des tâches ou du barème ouvre une nouvelle comparaison. Les poids d'origine ne sont jamais modifiés.

## Commandes

Depuis la racine de cette repo :

```powershell
python -m pytest -q
python -m unittest harness.test_harness -v
```

`pytest` est rouge avant patch (pricing, tags, tax échouent) et vert après patch correct. `unittest` teste la boucle d'outils et le grading sans modèle ni GPU.
