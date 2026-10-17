# Matrice de spécialisation (frontières posées le 17/10/2026)

Les 4 skills homonymes (présents au workspace ET au plateau opencode) ont désormais des domaines distincts, écrits dans leurs `SKILL.md` `description:` (les deux copies restent synchronisées, `diff` exit 0).

| Skill | Domaine naturel | Prend, ne prend PAS |
|---|---|---|
| `xdna2-evidence-oracle` | La **preuve locale** du workspace (rapports, URLs citées, empreintes, dates, ledger EVD, contradictions documentaires) | prend : interrogation ciblée des sources. ne prend PAS : exploration récursive de dépôts Git distants (déléguit à `git-ecosystem-investigator`) |
| `xdna2-path-explorer` | Les **plans et chemins matériels** XDNA2 (XRT/MCDM/DMA/BD/SRAM/memtile, soumissions, hybridation CPU/GPU/NPU) | ne prend PAS : la vérification documentaire (oracle) ni l'arbitrage inter-skills (cross-audit) |
| `xdna2-cross-audit` | La **décision** : matrice affirmation → preuve → statut → expérience discriminante, arbitrage des contradictions | n'exécute PAS les collectes lui-même (orchestration pure) |
| `git-ecosystem-investigator` | L'**archéologie des dépôts Git distants** (serveurs Git, API, issues/PR/releases, graphe d'écosystème) | ne prend PAS : la vérification du ledger EVD local, les plans d'expériences, l'arbitrage inter-skills |

Détail des 4 comparaisons homonymes (preuve bit à bit) : `evidence/homonym-skills-diff.json` — 3 identiques, 1 divergente (dérive synchronisée le jour même).

## Dépôt des rapports
Chaque mission = un dossier distinct `audits/<mission>/<horodatage>/` dans `C:/Users/videl/skills-audit-reports` (git dédié : `INDEX.md` racine, un commit par mission). Upstream déclaré du skill : https://github.com/Tagman45/investigator — **arbre vide aujourd'hui** (README 1 ligne, zéro script/tag) : toute mise à jour upstream devra passer par ce dépôt dédié pour la traçabilité.
