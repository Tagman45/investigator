# Plan d'expérience discriminant — proposé par le rôle `xdna2-path-explorer` (17/10/2026)

Fondé sur un blocage ouvert réel et récent (pas une digression : le dernier PASS du runtime, EVD-20261017-007, laisse un écart non expliqué).

## Question discriminante
**Les pics `embed` du run SFT (243 ms puis 130 ms sur steps @4 et @7, cf. `/e/qwen35_4b_run_sft-open.log`) sont-ils des relectures disque (HDD froid) ou du travail host H2D récurrent ?**

## Hypothèses en concurrence
| H | Mécanisme | Prédiction discriminante |
|---|---|---|
| H1 | Reads froides du HDD USB (page cache dégagé) | Pic moyen décroissant avec les relectures ; warm run : pics absents |
| H2 | Allocations/H2D host (Python/allocator) | Pics présents aussi sur warm run, à la même périodicité |
| H3 | Événements driver/NPU (récupération ERT) | Pics corrélés aux compteurs driver (xrt-smi), pas aux reads f=blob |

## Plan borné (lecture seule, ~10 min, pas de risque matériel)
1. **Run 1 froid** (post-reboot ou cache dégagé) : 3 tokens prefill, 12 steps decode, `--ids 1,2,3 --max-tokens 12` sur le conteneur `Qwen3.5-4B-SFT-open` (déjà validé EVD-007) — log step-timing détaillé.
2. **Run 2 immédiatement après** (chaud) : mêmes réglages.
3. **Mesure** : moyenne + variance des `embed` ms par step, froid vs chaud ; corrélation pic ↔ step sans autre composante part1/lm_head modifiée.
4. **Critère** : replanification repeatability — si les pics disparaissent à chaud : H1 validée (rien à débloquer, seulement les chiffres débit à corriger sur step pur ≈ 82 ms) ; si les pics demeurent à chaud : OUVRE une investigation H2/H3 (allocator, driver) dans une mission dédiée.
5. **Preuves à écrire** : 2 logs + JSON de résumé (statistiques froid/chaud) dans `audits/xdna2-project-mission-…/evidence/embed_spikes/`.

## Bornes de sécurité
Aucune écriture hors du dossier d'""evidence" de la mission ; aucun reflash, aucune modification du fork (règle du 17/10) ; NPU jamais tenu sous charge prolongée (run ≤ 1 min).
