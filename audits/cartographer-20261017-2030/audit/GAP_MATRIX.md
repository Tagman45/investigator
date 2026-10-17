# GAP MATRIX — exigences → capacités (livrable 2/8)

Légende : ✅ couvert · 🔶 partiel (étendre) · ❌ manquant (créer, minimal).

| # | Exigence mission | Capacité existante | Écart | Décision |
|---|---|---|---|---|
| 1 | Découverte/inventaire (branches, commits, langages, entry points, fichiers, symboles, dépendances, tests, builds, workflows, refs externes) | `inspect_repository` (fichiers, manifests, imports, log borné) | 🔶 langages/entry points/CI-tests/dépendances parsées/symboles absents | **ÉTENDRE** `inspect_repository.py` (champs ajoutés, sortie compatible) |
| 2 | Parser diagrammes existants → normaliser (IDs stables, identité repo, chemins, symboles, lignes, URLs, commit/ref, méthode, provenance) | `build_ecosystem_graph.build()` (schéma v1, IDs stables) | ❌ aucune grammaire Mermaid | **CRÉER** `parse_mermaid.py` (~150 lignes) branché sur `build()` |
| 3 | Vues liées (per-repo, écosystème, flows, dépendances, histoire, couverture, non-résolus) | `diagram_local.py` + `build_ecosystem_graph` (mmd/dot/json) | 🔶 une seule vue générique, pas de filtres | **ÉTENDRE** `build_ecosystem_graph.py` (`--view`, mêmes formats) |
| 4 | Corréler diagrammes↔code (jamais edge/README/200 comme preuve) | `diagram_local` (INFERRED systématique) | ❌ pas de confrontation edge↔fichiers/imports/manifests | **CRÉER** `correlate.py` (6 statuts + evidence/counter-evidence) |
| 5 | Statuts claims/edges + evidence/counter-evidence, raisons d'incertitude, transitions | `verify_bilan` (5 statuts, garde anti-suspens) | 🔶 STALE/CONFLICTING/MISSING + transitions absents | **ÉTENDRE** `verify_bilan.py` (pas de 2e oracle) |
| 6 | Comparer branches/commits/forks (déplacés/supprimés, drift, doublons, régressions) | `compare_repos` (heuristique chemins) + log git brut | ❌ pas de diff git confirmé | **CRÉER** `diff_repos.py` (git diff/moved/SHA) |
| 7 | Exports validés déterministes (Mermaid/JSON/MD/inventaires/ledgers/couverture) | `graph_validate` (extrémités/preuves/parité/complétude) | 🔶 transitions de statuts non validées | **ÉTENDRE** `graph_validate.py` (`--check-transitions`) |
| 8 | Plugins/adapters (langages, formats, plateformes, profils domaine) | engine `domains/*.json` + `adapters/` | 🔶 pas de registre formats/diagrammes | **ÉTENDRE** engine (registre `formats/`, même pattern) |
| 9 | Partiel/offline/permissions (inaccessibles, rate limits, troncatures, pagination, formats non supportés) | engine `--no-network` + `limits` + UNKNOWN-honnête | 🔶 champs de limites non normalisés | **ÉTENDRE** schéma `limits` (liste fermée de codes) |
| 10 | Intégration REA (traçabilité, reproductibilité, régressions, couverture, next) | engine + `coverage_report` + `prior_works` | ✅ couvert | **RÉUTILISER** (commande `map` les enchaîne) |

**Verdict** : 1 couvert, 6 à étendre, 3 à créer (dont 2 petits). Zéro duplication : chaque nouveauté se branche sur un module existant.
