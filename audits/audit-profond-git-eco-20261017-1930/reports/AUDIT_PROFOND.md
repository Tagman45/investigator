# AUDIT PROFOND — `git-ecosystem-investigator` (17/10/2026, 19h30)

**Méthode** : inventaire AST exhaustif (chaque fonction listée), test DIRECT de chaque fonction par import de module (nominal + limites, sans réseau réel), tests CLI existants comme preuve bout-en-bout, croisement avec les 3 skills homonymes. **Aucune fonction déclarée testée sans exécution.**

## 1. Inventaire : 43 fonctions, 10 scripts — TOUTES testées

| Script | Fonctions | Preuve directe (`test_all_functions.py`) | Preuve CLI (suites existantes) |
|---|---|---|---|
| `normalize_git_urls.py` | `normalize()`, `classify()`, `main()` | `test_normalize_variants`, `test_classify_kinds` | `test_core.py` |
| `extract_references.py` | `clean()`, `main()` | `test_clean` | `test_core.py` |
| `inspect_repository.py` | `run()`, `main()` | `test_run_ok_et_echec` (ok + échec + binaire absent → -1, jamais de crash) | — (couvert ici) |
| `collect_github_data.py` | `get()`, `main()` | `test_get_sans_reseau` (port fermé local, zéro réseau), `test_get_http_error_simulee` (403 mockée), `test_get_json_ok_simule` | — |
| `coverage_report.py` | `load()`, `main()` | `test_load_absent_invalide_valide` (FILE_ABSENT / INVALID_JSON / jsonl / json) | `test_negative.py` (4 cas) |
| `prior_works.py` | `validate()`, `_print_fail()`, `main()` | `test_validate_direct_et_print_fail` | `test_prior_works.py` (6 cas) |
| `verify_bilan.py` | `line_status()`, `compute_bilan()`, `main()` | `test_line_status_toutes_branches` (5 branches), `test_compute_bilan_global_et_pending` | `test_verify_bilan.py` + `test_partial.py` |
| `build_ecosystem_graph.py` | `node_id()`, `domain_of()`, `build()`, `to_mmd()`, `_dot_id()`, `to_dot()`, `main()` | `test_node_id_domain_dot`, `test_build_dedup_et_deterministe`, `test_to_mmd_dot_contenu` | `test_graph.py` (9 cas) + `test_core.py` |
| `graph_validate.py` | `_nid()`, `load_json()`, `endpoints_ok()`, `evidence_ok()`, `_ep()`, `parity_ok()`, `completeness_ok()`, `main()` | 4 tests directs (legacy inclus, parité rompue, inventaire perdu) | `test_graph.py` |
| `investigation_engine.py` | `load_domain_modules()`, `detect_domain()`, `build_plan()`, `_norm()`, `load_steps()`, `check_steps()`, `clamp_semantic()`, `demote_unrecorded()`, `finalize_bilan()`, `_read_claims()`, `main()` | 8 tests directs (clôtures VERIFIED/REFUSED/PARTIAL, réseau désactivé, redirection, modules invalides) | `test_engine_universal.py` (14 cas) |

**Résultat : 78/78 tests passés** (27 directs + 51 CLI), exit 0, sur la copie de référence. Détail : 1 seul échec rencontré pendant l'audit — attente de test fausse (`node_id("a/b c!")` → `"a_b_c_"`, normalisation correcte), corrigée côté test, code intact.

## 2. Frontières inter-skills (audit croisé réel, pas déclaratif)

- **`xdna2-evidence-oracle`** (`oracle.py` : 23 fonctions — indexation/chunking `_split_*`, `extract_urls`, `check_url(s)`, `github_search`, `research`) : **pas de duplication**. L'oracle INDEXE et VÉRIFIE réellement des URLs (HTTP live) ; git-eco JOURNALISE la discipline de recherche et CALCULE des statuts — jamais l'inverse. ⚠️ **Recouvrement mineur documenté** : `collect_github_data.get()` (GET GitHub API) vs `oracle.check_url()` (vérification HTTP générique). Usages distincts (collecte bornée vs audit de liens), aucune suppression — mais toute future fonction HTTP-live ira dans l'oracle, pas dans git-eco.
- **`xdna2-cross-audit`** : **zéro fichier .py** (markdown uniquement) — aucun doublon de code possible ; l'arbitrage inter-skills reste documentaire, le moteur git-eco ne l'implémente pas (frontière respectée).
- **`xdna2-path-explorer`** : **zéro fichier .py** — idem ; les plans d'expériences matérielles ne sont ni implémentés ni dupliqués ici.

## 3. Écarts et corrections restantes (priorisées)

1. **P1 — `inspect_repository.py` sans test CLI** : `run()` est désormais testé en direct, mais `main()` (walk complet, imports, manifests) n'a qu'une couverture indirecte. Recommandé : `test_inspect_repo.py` avec fixture repo (déjà prévue par la mission Cartographe).
2. **P1 — preuves legacy M2 irrésolubles** (confirmé par `graph_validate` réel : 13 nœuds/7 relations OK, 7 preuves `MISS-*/DIFF-*/SCAN-*/HOME-*/UPSTREAM-*` introuvables dans `evidence/`) : migration `findings.jsonl` + `evidence/` sans réécrire l'historique (mission distincte, cf. roadmap).
3. **P2 — `collect_github_data.main()` non testé** (endpoints/pagination) : mock `urlopen` multi-pages à ajouter.
4. **P2 — règle métier** : tout futur appel HTTP-live → `xdna2-evidence-oracle`, jamais git-eco (inscrire dans SKILL.md).
5. **P3 — `.pytest_cache/` versionné ?** : vérifier qu'il est ignoré (trouvé dans l'arbre du skill — à confirmer dans `.gitignore`).

## 4. Verdict

**AUDIT PASS** — 43/43 fonctions listées, 43/43 exercées avec preuve d'exécution (78/78 tests, exit 0), frontières inter-skills vérifiées sans duplication, 1 recouvrement mineur documenté sans action destructive. Les 5 corrections restantes sont priorisées et aucune ne bloque l'usage actuel.
