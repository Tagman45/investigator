# AUDIT — implémentation actuelle + historique Git (livrable 1/8)

Date : 17/10/2026, 20h30. Périmètre : `skills/local/git-ecosystem-investigator/` (copie de référence ; miroirs insight + backup synchronisés SHA).

## 1. Historique Git pertinent

| Commit | Objet |
|---|---|
| `ecefb05` | Intégration initiale du skill (EVD-009/010, fix regex `inspect_repository.py`), spécialisation des 4 skills homonymes |
| `005c055…8feb54c` + `417ebfd` | Cycles auto-commit (correctifs mineurs) |
| `1fd359a` | **Moteur universel** `investigation_engine.py` (détection modulaire, profils, garde-fou au point d'entrée) |
| `d016e3c` | **Graphe à IDs stables** (`build_ecosystem_graph.py` mmd+dot+JSON, `graph_validate.py`) |
| `546b2a3` | `test_all_functions.py` (43 fonctions en direct), `diagram_local.py` + `compare_repos.py`, fix Unicode `inspect_repository.py` |

État : 86/86 tests verts sur les 3 copies. Aucune spécialisation XDNA2 dans le cœur (interdit par test).

## 2. Capacités existantes réutilisables (pas de duplication)

| Module | Capacité prouvée | Réutilisation Cartographe |
|---|---|---|
| `inspect_repository.py` (37→~40 lignes) | walk read-only, manifests, imports, historique git borné, JSON ASCII-safe | **Base de l'inventaire** — à étendre (langages, entry points, CI/tests, dépendances parsées), pas à remplacer |
| `normalize_git_urls.py` | canonisation + classification GitHub | Identité des dépôts (exigence : repository identity) |
| `extract_references.py` | URLs/md/html + refs GitHub avec lignes + contexte | Extraction des pistes (docs, diffs, manifests) |
| `collect_github_data.py` | REST bornée, pagination, erreurs | Collecte distante (branches/tags/releases/PRs) — inchangé |
| `diagram_local.py` | Mermaid local depuis inspection, arêtes INFERRED | **Génération de vues** — à étendre (`--view`), pas à dupliquer |
| `compare_repos.py` | Jaccard, communs/uniques, manifests, moved-candidates | **Base du diff structurel** — à compléter par `diff_repos.py` côté git |
| `build_ecosystem_graph.py` | schéma v1 IDs stables, mmd+dot+JSON paritaires | **Schéma canonique** — à étendre (champs version/commit/symboles/lignes) |
| `graph_validate.py` | extrémités, preuves, parité, complétude, legacy | **Validation** — à étendre (transitions de statuts) |
| `investigation_engine.py` | detect/plan/check/bilan, garde-fou, profils, modules `domains/` | **Orchestrateur** — commande `map` + registre `formats/` sur le même pattern |
| `verify_bilan.py` | 5 statuts calculés + garde anti-suspens | **Registre de statuts** — à étendre (STALE/CONFLICTING/MISSING), pas de 2e oracle |
| `coverage_report.py` / `prior_works.py` | couverture UNKNOWN-honnête, section travaux antérieurs | Intégration REA — inchangés |

## 3. Conventions REA observées (à préserver)

- Preuve avant/après, exit codes préservés, jamais de test affaibli pour passer.
- Statuts calculés, jamais déclarés ; absence ≠ preuve ; HTTP 200 ≠ validation.
- Diffusion one-way référence → insight → backup, SHA vérifiés.
- Rapports par mission horodatée + INDEX.md ; historique jamais réécrit.

## 4. Points durs identifiés

- `inspect_repository.main()` sans test CLI dédié (P1 audit précédent).
- Preuves legacy M2 irrésolubles (finding consigné, migration à part).
- `collect_github_data.main()` (pagination) sans test mocké.
- Aucune grammaire Mermaid existante : le parse de diagrammes est à créer.
- Aucun diff git structurel (renommés/déplacés confirmés par git, pas par heuristique).
