# MISSION — AMÉLIORER LE SKILL doc-skill-xdna2
Rapport REA · 18/10/2026 · périmètre : `skills/local/git-ecosystem-investigator/`

## Travaux antérieurs et réutilisation des preuves

| Nom du travail | Référence | Identifiants | Résultat antérieur | Lien avec la mission actuelle | Action restante | Provenance | Vérification |
|---|---|---|---|---|---|---|---|
| M4 — mission cartographe | `audits/cartographer-20261017-2030/` (commit local `3ddc089`) | EVD-2026-CARTO | 110/110 tests, `map`, `correlate`, `diff_repos`, `formats/mermaid.json` livrés ; evidence/ et fixtures/ vides | Base directe : les modules existants sont étendus, pas dupliqués | combler les preuves (fait ici) | commit local + SHA du manifeste | VERIFIED (18/10, relu les 3 rapports M4) |
| M2 — audit de tous les skills | `audits/all-skills-20261017-1800/` | EVD-20261017-010 | 4 liens morts, 1 dérive de synchronisation corrigée, matrice de spécialisation | Frontières inter-skills respectées (aucun doublon de l'oracle) | — | commit `0b08de0` | VERIFIED (18/10, INDEX + rapport) |
| M3 — pilote moteur universel | `audits/investigation-universelle-pilote-20261017-191211/` | EVD-2026-PILOTE | 42/42 tests, 3 bilans VERIFIED, garde-fou de clôture | Le garde-fou n'est pas retouché ; seules les sources nouvelles sont branchées | — | commit `d58fa3c` | VERIFIED (18/10) |
| `xdna2-evidence-oracle` (skill local) | `skills/local/xdna2-evidence-oracle/SKILL.md` | — | Niveau 1-3 : index local, check-urls, veille | Frontière : l'oracle = preuves LOCALES ; le module arXiv ajouté ici = sources SCIENTIFIQUES distantes, avec Sha/pdf | ne pas fusionner les deux | lecture directe du SKILL.md | VERIFIED (18/10, lu en entier) |
| `xdna2-cross-audit` (skill local) | `skills/local/xdna2-cross-audit/SKILL.md` | — | Matrice affirmation → preuve → source → statut | Confirme que la littérature se cite avec statut, jamais comme mesure | — | lecture directe | VERIFIED (18/10) |
| Correction 404 `doc-skill-xdna2` | `audits/cartographer-20261017-2030/reports/CROISE_ANNEXE_MD.md` §A | commit `2924d95` | Le dépôt existe mais est PRIVÉ (404 anonyme) | Le push de cette mission est autorisé et possible | push effectué (voir §5) | `gh api` + `git ls-remote` | VERIFIED (18/10) |

## 1. Audit initial du skill (lecture seule, avant modification)

Chemin réel : `C:/Users/videl/Desktop/doc-skill-xdna2-work/skills/local/git-ecosystem-investigator`
Dépôt : `doc-skill-xdna2-work` (branche `main`), remote `Tagman45/doc-skill-xdna2` (**privé**, vérifié authentifié).
Copies : `.config/opencode/skills/git-ecosystem-investigator` (insight), `skills_backup/opencode/...` (backup).

| Capacité | Implémentation | Preuve | Test | Lacune | Priorité |
|---|---|---|---|---|---|
| Inventaire dépôt (fichiers, manifests, imports, git log) | `inspect_repository.py` | JSON `languages/entry_points/ci/tests/dependencies/limits` | `test_inspect_champs_cartographe` | CI limitée à des marqueurs de chemin (Actions/GitLab/Azure/Jenkins partiels) | P2 |
| Diagramme local | `diagram_local.py` | mmd+dot+json | `test_vues_filtres` | **jamais appelé par `map`** → le skill ne générait aucun diagramme | **P0** |
| Parsing Mermaid | `parse_mermaid.py` | rows schéma v1 | 3 tests | labels déclarés sur lignes séparées **perdus** → corrélation impossible | **P0** |
| Corrélation diagramme↔code | `correlate.py` | 6 statuts | 6 tests | résolution échouait sur préfixes `repo:`/`internal:` | **P0** |
| Graphe + vues + parité | `build_ecosystem_graph.py` | mmd/dot/json | 8 tests | vues OK ; pas de `--dot` par vue (parité non vérifiable par vue) | P1 |
| Diff git | `diff_repos.py` | `git diff --name-status -M` | 4 tests | — | — |
| Couverture + codes de limites | `coverage_report.py` | `LIMIT_CODES` | `test_codes_limites_fermes` | 10 codes seulement : aucun pour réseau/PDF/API | **P1** |
| Bilan / statuts | `verify_bilan.py`, engine | statuts calculés | 9 + 12 tests | — | — |
| **Récupération web** | **absente** | — | — | aucun module HTTP classifié, aucun plafond, aucun SHA | **P0** |
| **PDF scientifique** | **absent** | — | — | aucune extraction, aucune vérification de validité | **P0** |
| **Recherche arXiv** | **absente** | — | — | aucune source scientifique, aucune gestion de versions | **P0** |
| Preuves de mission (M4) | `evidence/` et `fixtures/` | dossiers **vides** | — | manque de traçabilité | **P1** |

Baseline exécutée AVANT modification (commit `7e1a887`) : `python -m pytest tests -q` → **110 passed**.

## 2. Lacunes confirmées et leurs preuves

| # | Lacune | Preuve mesurée | Correctif |
|---|---|---|---|
| L1 | `map` ne génère aucun diagramme | `cmd_map` n'appelait que `parse_mermaid` sur les `.mmd` existants ; un dépôt sans `.mmd` produisait `ledgers: []` (test d'origine) | génération `diagram_local` par dépôt, journalisée |
| L2 | Auto-ingestion des artefacts | 2ᵉ passage de `map` : **258 → 2591 arêtes** (le graphe relisait `view_*.mmd`/`diagram_*.mmd` qu'il venait d'écrire) | exclusion de `out_dir` + stems générés |
| L3 | Corrélation faussement `MISSING` | sur le dépôt du skill : **256 / 258 arêtes MISSING** alors que tous les fichiers existaient | backfill des labels + normalisation `repo:`/`internal:` + racine + suffixe |
| L4 | Aucune résilience web | aucun module HTTP ; un 403/404/timeout aurait fait échouer ou mentir | `web_fetch.py` |
| L5 | Aucune lecture PDF | aucun code PDF dans le skill | `pdf_extract.py` |
| L6 | Aucune source scientifique | 0 article arXiv citable | `arxiv_search.py` |
| L7 | Faux positifs lexicaux arXiv | requête NPU/LLM : **5 / 8 résultats = physique des particules** | filtre lexical déclaré `--require/--exclude` |
| L8 | Preuves de mission vides | `ls evidence/ fixtures/` → vides (mission M4) | manifeste SHA-256 + fixtures copiées + journal de commandes |
| L9 | Codes de limites incomplets | 10 codes, aucun réseau/PDF | +11 codes fermés |

## 3. Modifications et justification

| Fichier | Nature | Justification |
|---|---|---|
| `scripts/web_fetch.py` | **créé** | résilience : réessais bornés, 403 sans contournement, 429 ralenti, 404 ≠ inexistence, 200-vide détecté, SHA-256, plafonds deadline/taille |
| `scripts/pdf_extract.py` | **créé** | validité PDF (signature + `%%EOF`), texte page par page, `text_consulted` honnête, HTML déguisé détecté |
| `scripts/arxiv_search.py` | **créé** | API Atom, versions dédupliquées avec historique, PDF vérifié, références candidates, lien technique déclaré, filtre lexical mesuré |
| `scripts/coverage_report.py` | étendu | +11 codes fermés (réseau, PDF, API, conflits) — aucune régression des 10 existants |
| `scripts/parse_mermaid.py` | corrigé | backfill des labels déclarés hors ligne d'arête (cause de L3) |
| `scripts/correlate.py` | corrigé | normalisation des préfixes, résolution racine/dossier/suffixe (cause de L3) |
| `scripts/investigation_engine.py` | étendu | génération de diagrammes + exclusion des artefacts propres (L1, L2) |
| `scripts/inspect_repository.py` | étendu | ignore `.pytest_cache/.mypy_cache/.ruff_cache` (bruit dans l'inventaire) |
| `tests/test_web_science.py` | **créé** | 25 tests ciblés (serveur HTTP local réel, PDF, Atom figé, filtre) |
| `tests/conftest.py` | **créé** | marker `network` (tests réels sautés si injoignable) |
| `tests/fixtures/arxiv/atom_1706.03762.xml` | **créé** | réponse Atom réelle figée (SHA `9e39b109…5eed`, collectée 18/10) |
| `tests/test_cartographer.py` | adapté | 3 tests encodaient l'ancien comportement (pas de diagramme) → réécrits pour le nouveau, sans affaiblir les assertions |
| `SKILL.md`, `references/web-science.md` | doc | contrats, niveaux de lecture, table des comportements d'échec |

Aucun doublon de `xdna2-evidence-oracle` : l'oracle reste l'index des preuves LOCALES ; les nouveaux modules traitent des sources DISTANTES (HTTP/PDF/arXiv).

## 4. Fichiers modifiés et diff

`git diff --stat` (dépôt `doc-skill-xdna2-work`, copie de référence) :

```
 SKILL.md                        | 36 ++++
 scripts/correlate.py            | 54 +++++-
 scripts/coverage_report.py      | 34 ++--
 scripts/inspect_repository.py   |  3 +-
 scripts/investigation_engine.py | 53 +++++-
 scripts/parse_mermaid.py        | 16 ++
 tests/test_cartographer.py      | 34 +++-
```
Nouveaux : `web_fetch.py`, `pdf_extract.py`, `arxiv_search.py`, `tests/test_web_science.py`,
`tests/conftest.py`, `tests/fixtures/arxiv/`, `references/web-science.md`.

Les deux copies (insight, backup) ont été resynchronisées puis vérifiées **SHA-256 identiques**
(57 fichiers ; la copie backup était en retard et a été remise à niveau).

## 5. Tests exécutés — commandes, codes de sortie, résultats

| Commande | Résultat | Exit |
|---|---|---|
| `pytest tests -q` (AVANT, `7e1a887`) | 110 passed | 0 |
| `pytest tests -q` (référence, après) | **135 passed** in 17.9 s | 0 |
| `pytest tests -q` (copie `.config/opencode/skills/…`) | 135 passed | 0 |
| `pytest tests -q` (copie `skills_backup/opencode/…`) | 135 passed | 0 |
| `arxiv_search.py id 1706.03762 --fetch-pdf --references` | 1 article, **15 pages**, 39 496 caractères, SHA PDF `bdfaa68d…f697`, 23 références candidates, `PDF_FULLTEXT` | 0 |
| `arxiv_search.py search "NPU accelerator …" --max 8 --require npu llm …` | 8 → **3 retenus / 5 écartés motivés** | 0 |
| `investigation_engine.py map --repos <skill> <audit>` | `steps.jsonl` sans étape manquante ; diagrammes générés | 0 |
| `graph_validate.py --graph view_ecosystem.json --mmd …` | PASS (aucun échec) | 0 |
| `graph_validate.py` avec un `.dot` d'un **autre** graphe | FAIL « parité dot rompue » — usage erroné de ma part, pas un défaut du module | 1 |

## 6. Comparaison avant / après (mêmes dépôts)

| Métrique | Avant | Après | Comment mesuré |
|---|---|---|---|
| Tests du skill | 110 | **135** (+25) | `pytest -q`, 3 copies |
| Diagrammes générés par `map` | 0 | **1 par dépôt** (`diagram_<repo>.mmd/.json/.dot`) | `map_summary.json → generated_diagrams` |
| Arêtes `MISSING` sur le dépôt du skill | 256 / 258 (99 %) | **1 / 33** (le seul vrai manquant : fixture `gone.py`) | `correlated.json` |
| Croissance du graphe à l'exécution répétée | 258 → 2591 (×10) | 33 → 42, **entièrement expliqué** par 4 imports du nouveau test + 1 fixture copiée (diff d'ensembles) | comparaison `source_label/target_label` |
| Faux positifs arXiv (requête NPU/LLM) | 5 / 8 (physique des particules) | **0 / 3** retenus | `lexical_filter.dropped_entries` |
| Preuves de mission M4 | 0 fichier | **63 entrées SHA-256** + journal de commandes + fixtures | `evidence/MANIFEST_SHA256.txt` (régénéré 18/10, vérifié 63/63) |
| Preuves de cette mission | — | **94 entrées SHA-256** (skill + tests + livrables) | `evidence/MANIFEST_SHA256_M6.txt` (vérifié 94/94) |
| Codes de limites fermés | 10 | **21** | `coverage_report.LIMIT_CODES` |

## 7. Limites restantes et recommandations

| # | Limite | Impact | Recommandation | Priorité |
|---|---|---|---|---|
| R1 | La classification d'échec réseau est testée sur serveur local, pas contre les CDN réels (403/429 réels d'éditeurs) | comportement réel non mesuré à grande échelle | campagne `web_fetch` sur 20 URLs de `SOURCES_MASTER.md` avec relevé de codes | P1 |
| R2 | Extraction PDF dépend de `pypdf` (absent → `PDF_TEXT_UNAVAILABLE`) | pas de texte sans la dépendance | épingler `pypdf` dans un `requirements-optional.txt` et le documenter | P2 |
| R3 | Tableaux/figures/formules non extraits de façon fiable | un chiffre lu dans un tableau doit être vérifié visuellement | `visual_pages_pending` déjà émis ; ajouter une passe de rendu page→image (hors périmètre ici) | P1 |
| R4 | Filtre arXiv lexical (pas sémantique) | peut écarter un article pertinent sans le mot-clé | conserver `--require` explicite et lire les `dropped_entries` | P2 |
| R5 | `build_ecosystem_graph` n'émet pas de `.dot` par vue → la parité par vue n'est pas vérifiable | trou de validation | ajouter `--dot-out` aux vues générées par `map` | P1 |
| R6 | Une arête auto-référente (`api.py → api.py`) apparaît sur les fixtures copiées | bruit mineur | filtrer `source_id == target_id` dans `diagram_local` | P2 |
| R7 | Aucune expérience NPU exécutée dans cette mission | les nouveaux modules ne prouvent rien sur le matériel | mission séparée, avec le garde-fou runtime existant | — |

## 8. Note argumentée : **82 / 100**

| Critère | Poids | Note | Justification (preuve) |
|---|---|---|---|
| Lacunes réellement corrigées (mesurées) | 25 | 22 | 3 défauts P0 corrigés avec avant/après chiffré (§6) |
| Traçabilité des preuves | 15 | 13 | SHA-256 (manifestes 63 + 94 entrées, PDF, Atom), dates, commandes + exits |
| Honnêteté des statuts (pas de faux succès) | 15 | 14 | `EMPTY_CONTENT`, `HTTP_404`, `PDF_PARTIAL`, `text_consulted`, test « simulé » nommé |
| Couverture de tests | 15 | 12 | 25 tests, mais erreurs réseau réelles seulement locales (R1) |
| Absence de duplication inter-skills | 10 | 9 | frontière oracle/arXiv explicitée et respectée |
| Résilience web | 10 | 8 | plafonds + classification complets ; non éprouvé à l'échelle (R1) |
| Valeur scientifique (arXiv) | 10 | 6 | métadonnées/PDF/versions solides ; pas de rendu visuel des tableaux (R3) |
| **Total** | **100** | **82** | |

Retraits assumés : −6 (pas de mesure réelle d'erreurs réseau à l'échelle), −4 (pas de vérification visuelle des tableaux/figures), −3 (parité dot par vue), −3 (dépendance PDF optionnelle), −2 (bruit auto-référent).

## 9. Verdict

**ACCEPT** — les lacunes P0 sont corrigées et mesurées (corrélation 256→1 `MISSING`, génération de diagrammes effective, résilience web et lecture scientifique ajoutées sans doublon), la suite passe de 110 à 135 tests sur les trois copies, les preuves de mission ne sont plus vides. Les points R1/R3/R5 restent ouverts et sont explicitement recommandés comme prochaine mission (aucune conclusion runtime n'est tirée ici).
