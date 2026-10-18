# Skills disponibles et usage RÉEL dans cette mission (18/10/2026)

Inventaire fait sur disque (`C:/Users/videl/.config/opencode/skills` et
`skills/local`). « Utilisé » signifie : lu, et son contenu a changé une
décision ou un livrable de cette mission — pas seulement ouvert.

| Skill | Emplacement | Usage dans cette mission | Preuve |
|---|---|---|---|
| `git-ecosystem-investigator` | `skills/local/…` | **cible principale** : audité puis étendu (web/PDF/arXiv, génération de diagrammes, corrélation) | 135 tests, `map` sur 2 dépôts réels |
| `xdna2-evidence-oracle` | `skills/local/…` + `.config/opencode/skills` | lu comme FRONTIÈRE : ne pas dupliquer l'index local ni `check-urls` ; le module arXiv a été placé côté sources distantes | §3 du rapport, frontière explicite |
| `xdna2-cross-audit` | idem | lu pour la règle « matrice affirmation → preuve → source → statut » ; appliquée à la note /100 et aux statuts | §8 du rapport |
| `evidence` | `.config/opencode/skills/evidence` | règle de statut de preuve reprise (source/hypothèse/preuve) | `text_consulted`, `lexical_relevance` |
| `search-policy` | `.config/opencode/skills/search-policy` | règle de politesse API (User-Agent identifiable, 3 s entre requêtes arXiv) | `POLITE_DELAY`, `UA` |
| `xdna2-path-explorer` | idem | **non utilisé** : chemins matériels XRT/DMA hors périmètre de cette mission (aucune expérience NPU exécutée) | R7 du rapport |
| `token-scout`, `nitro-writer`, `1bit-writer`, `npu-offload-pipeline`, `open-granite-kernels`, `open-phi3-nanbeige-kernels`, `open-qwen36-kernels`, `aie2p-hand-asm-debug`, `debug-method`, `oracle-query`, `op15-apk-debug` | idem | **non utilisés** : sans rapport avec un audit de skill documentaire (noyaux AIE, rédaction Nitro, APK Android, modèles) | absence d'emploi = assumée, pas dissimulée |

## Conséquence sur les livrables

Les skills « métier » (noyaux, rédaction, APK) n'auraient apporté aucune
preuve supplémentaire à un audit de skill Python documentaire : les
mobiliser aurait produit du volume sans améliorer le rapport, ce que la
mission interdit explicitement. Les skills utiles (`git-ecosystem-investigator`,
`xdna2-evidence-oracle`, `xdna2-cross-audit`, `evidence`, `search-policy`)
ont chacun laissé une trace vérifiable ci-dessus.
