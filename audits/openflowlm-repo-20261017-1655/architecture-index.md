# Architecture index — OpenFlowLM-Next (vue issue du test du skill)

Construite uniquement à partir des objets localement vérifiés (pass 2 `src/`, `repository-inspect-src.json`). Un diagramme n'est pas une preuve d'exécution (règle du skill).

## Moteur `src/open_qwen36/` (24 fichiers, CONFIRMED_STATIC)
| Composant | Fichiers | Rôle (d'après le code inspecté aujourd'hui) |
|---|---|---|
| Noyau runtime | `core.cpp/.hpp`, `pools.cpp`, `manifest.cpp`, `q4nx_file.cpp`, `gguf_file.cpp` | résidence des pools de poids, dispatch XRT, parsing Q4NX/GGUF/manifest |
| Orchestration | `engine.cpp`, `cli.cpp`, `block_host.cpp/.hpp` | boucles prefill/decode, routes npu/host/auto, tests CLI |
| Vision | `vision/vit.cpp` | ViT sur le host |
| Tests | `*_test.cpp`, `pools_test.cpp` | surface CI du moteur |

## Écosystème externe (arêtes déclarées)
- `OpenFlowLM-Next` (notre travail) ⇒ fork de `Atomic-Germ/OpenFlowLM` (CONFIRMED_STATIC via git remote + docs)
- `Atomic-Germ/OpenFlowLM` ⇒ déclare descendre de `ROCm/FastFlowLM` (DECLARED, README)
- Distribution binaire : `Atomic-Germ/OpenFlowLM/releases/latest/download/oflm-setup.msi` (DECLARED, docs/index.md:17)
- Canal communauté : Discord `jtWZdMJ8ee` (DECLARED, docs/index.md:34)

## Liens vers le graphe
- `ecosystem-graph.mmd` : Mermaid généré par `build_ecosystem_graph.py` à partir de `connection-ledger.jsonl`.
- Chaque arête porte `type:certainty` ; les arêtes `UNKNOWN` (probe API) restent dans le graphe pour ne pas masquer l'échec HTTP_403.
