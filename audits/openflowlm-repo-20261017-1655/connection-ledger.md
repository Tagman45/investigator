# Connection ledger (rendu markdown)

Source de vérité machine : `connection-ledger.jsonl` (7 arêtes) et `url-discovery-ledger.jsonl` (11 destinations).

| # | Source | Destination | Relation | Certainty | Preuve |
|---|---|---|---|---|---|
| 1 | local:repos_openflowlm_next (git origin) | github.com/Atomic-Germ/OpenFlowLM-Next | is_local_clone_of | CONFIRMED_STATIC | URL-NEXT-001 |
| 2 | docs/index.md:17 | …/OpenFlowLM/releases/latest/download/oflm-setup.msi | distributes_binary | DECLARED | URL-003 |
| 3 | docs/index.md:21 | github.com/Atomic-Germ/OpenFlowLM | upstream_project | CONFIRMED_STATIC | URL-004 |
| 4 | README.md (l.5+) | github.com/ROCm/FastFlowLM | fork_parent | DECLARED | URL-004b |
| 5 | docs/index.md:34 | discord.com/invite/jtWZdMJ8ee | community_channel | DECLARED | URL-005 |
| 6 | github_api: repos/Atomic-Germ/OpenFlowLM-Next | api.github.com/… | api_probe | UNKNOWN (HTTP_403) | COLLECT-403 |
| 7 | src/open_qwen36 (24 fichiers) | …/tree/main/src/open_qwen36 | code_inventory | CONFIRMED_STATIC | INSPECT-SRC-001 |

## Statuts négatifs consignés
- `INACCESSIBLE` : API GitHub (5/5 endpoints `HTTP_403`, sans jeton — `GITHUB_TOKEN` non configuré, jamais imprimé).
- `OUT_OF_SCOPE` : 6 destinations média (5 youtu.be, 1 asset `user-attachments`, badge shields.io inclus dans les DECLARED).
- `NOT_YET_INSPECTED` : aucun restant sur les 11 destinations (mis à jour 2026-10-17).
