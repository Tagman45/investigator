# LACUNES.md — registre central des lacunes transversales

Un identifiant stable par lacune (`L-<priorité>-<n°>`), conservé même après clôture.
Une lacune peut concerner plusieurs missions : c'est le point de regroupement.
Statuts : `OUVERTE` · `EN COURS` · `CORRIGÉE (preuve)` · `REFUSÉE (justif.)` · `À REVÉRIFIER`.

**Règle** : le passage à `CORRIGÉE` exige la correction **et** sa validation (voir `CLOTURE.md`).
Un test vert ne suffit pas si le comportement demandé n'est pas exercé.

## P0 — compréhension et vérifiabilité du dépôt

| ID | Lacune | Preuve / source | Statut | Test de clôture |
|---|---|---|---|---|
| L-P0-01 | `README.md` réduit à un titre : ni architecture, ni commandes, ni limites | `README.md` (14 o) avant le 18/10 | **CORRIGÉE (preuve)** — README réécrit (rôle, structure, commandes, contrat de preuve, limites) | relecture du README + `python -m pytest tests -q` vert |
| L-P0-02 | `purpose.md` ne distinguait pas dépôt d'archives et dépôt du moteur | `purpose.md` (4 lignes) avant le 18/10 | **CORRIGÉE (preuve)** — périmètre, non-périmètre, contrat de structure, autorisation distante | relecture ; absence de consigne de modification de skill dans ce dépôt |
| L-P0-03 | Aucun registre central des lacunes : `INDEX.md` liste des missions, pas des problèmes | ce fichier (créé 18/10) | **CORRIGÉE (preuve)** — `LACUNES.md` | un identifiant cité depuis au moins deux missions |
| L-P0-04 | Aucun registre des preuves (sources, SHA-256, versions, limites) | `PREUVES.md` (créé 18/10) | **CORRIGÉE (preuve)** | au moins une entrée par campagne, avec code de sortie |
| L-P0-05 | Pas de règle de clôture opposable | `CLOTURE.md` (créé 18/10) | **CORRIGÉE (preuve)** | une lacune passée en `CORRIGÉE` avec correction + validation |
| L-P0-06 | Missions `M7` (`skills-contract-20261018`) et `M8` (`skills-fix-20261018`) absentes de l'arbre public au 18/10 | `git status` avant commit : dossiers non suivis | **À REVÉRIFIER** après push (le dossier doit apparaître dans `origin/main`) | `git ls-tree origin/main audits/` liste les deux dossiers |

## P1 — lacunes techniques relevées par les audits antérieurs

| ID | Lacune | Source | Statut | Test de clôture |
|---|---|---|---|---|
| L-P1-01 | Tests Web réels limités (erreurs HTTP éprouvées sur serveur local surtout) | rapport REA skill, audit M6 | **À REVÉRIFIER** | campagne bornée sur URL réelles, codes/redirections/délais conservés |
| L-P1-02 | Extraction PDF insuffisante pour tableaux/figures/formules | rapport REA skill | **OUVERTE** | rendu visuel des pages + vérification des chiffres clés |
| L-P1-03 | Parité des vues DOT non complètement vérifiable | rapport Cartographe / REA | **OUVERTE** | un DOT par vue + comparaison automatisée |
| L-P1-04 | Couverture GitHub partielle (HTTP 403 → issues/PR non collectées) | questions ouvertes OpenFlowLM | **OUVERTE** | collecte authentifiée paginée, statuts `INACCESSIBLE`/`UNKNOWN` préservés |
| L-P1-05 | Historique des dépôts : clones superficiels, renommages/migrations non prouvés | rapport Cartographe | **OUVERTE** | diffs Git réels + SHA de contenu + commits pertinents |
| L-P1-06 | `max_files` peut masquer des zones d'un gros dépôt | rapport Cartographe | **OUVERTE** | rapport de troncature explicite (fichiers ignorés listés) |
| L-P1-07 | Provenance des miroirs : 37 dépôts sans empreintes de contenu vérifiées | audit du 17/10 | **OUVERTE** | empreintes par dépôt + distinction clone prouvé / copie non prouvée |
| L-P1-08 | Recherche arXiv : filtre lexical, pas sémantique | audit M6 | **OUVERTE** | résultats rejetés conservés et inspectables |
| L-P1-09 | `pypdf` dépendance optionnelle non documentée en cas d'absence | audit M6 | **OUVERTE** | message d'indisponibilité + marche à suivre |
| L-P1-10 | Relations auto-référentes dans les graphes (bruit) | audit M6 | **OUVERTE** | filtre + comptage avant/après |
| L-P1-11 | Collecte distante : chemins CLI de pagination et cas d'erreur non testés de bout en bout | audit M6 / REA | **OUVERTE** | test CLI avec pagination + erreurs simulées |

## Lacunes propres au domaine XDNA2 (mission `xdna2-overhead-20261018`)

| ID | Lacune | Preuve | Statut | Test de clôture |
|---|---|---|---|---|
| L-X-01 | Pré-vol non *fail-closed* : `plancher mesuré > borne décodée` est signalé sans refus (pas de `FAIL_BOUND_CONFLICT`) | `npu_preflight.py:230,246` ; mesuré 18/10 sur design 512 (`arg1` : `desaccord_descripteur=true`, verdict `PASS`, exit 0) | **OUVERTE** | refus explicite + test négatif dédié |
| L-X-02 | Aucune sentinelle de fraîcheur : une même taille sous-dimensionnée peut produire 512 fausses valeurs **ou** un sha identique à la sortie correcte | `evidence/exp_P_order2.json` vs `exp_P_single_8372224.json` | **OUVERTE** | test qui refuse un résultat non frais (sentinelle + BO neufs) |
| L-X-03 | Borne décodée ignore `d0/d1/d2` : jamais un majorant | `npu_preflight.py` docstring `txn_extents` | **OUVERTE** | décodage complet + comparaison au besoin mesuré |
| L-X-04 | Mapping `bo0/bo1/bo2` ↔ A/B/C non prouvé côté design (défini par le harnais, indétectable numériquement car A et B valent tous deux 1,0) | `npu_gemm_ref.py:71-73,92` ; `kernels_main.json` (bo0..bo4) | **OUVERTE** | retrouver le `runtime_sequence` du design 512 ou différencier A/B par contenu |
| L-X-05 | RAG local inaccessible (`MemoryError`, index 686 Mo) ; `rag ofa` format incompatible | `JOURNAL_PHASE_B` B11-B12 | **OUVERTE** | requête RAG réussie documentée |
| L-X-06 | L'oracle ne constitue pas une validation externe (retrouve nos propres rapports) | `SOURCES_URLS_ET_AGENTS_2026-10-18.md` §4 | **OUVERTE** | indexer un corpus externe (issues/docs) |
| L-X-07 | Une seule source VÉRIFIÉE-HTTP sans contenu (dépôt `amd/xdna-driver`) | `evidence/urls/github.com_amd_xdna-driver.json` | **OUVERTE** | fetch du contenu avec extracteur adapté |
