# PREUVES.md — registre des preuves

Une entrée par campagne. Chaque entrée : source, objet, empreinte/version, commande exacte,
code de sortie, limites de consultation. Les sorties brutes vivent dans
`audits/<mission>/evidence/`.

## Environnement de référence (missions XDNA2)

| Élément | Valeur vérifiée |
|---|---|
| SoC | Ryzen AI 9 365 (Strix Point), NPU device 0x17F0 |
| Pilote NPU | 32.0.20101.3760 |
| Firmware NPU | 1.1.2.64 |
| XRT | 2.21.0 |
| OS | Windows 11 (bash Git Bash) |
| Design testé | `phase5_bf16_512x8192x512` (M=512, K=8192, N=512) |

## Campagnes

| # | Mission | Source/objet | Empreinte | Commande (code de sortie) | Limites |
|---|---|---|---|---|---|
| P-01 | `xdna2-overhead-20261018` | 12 pages externes (issues MLIR-AIE #3653/#3033/#3840/#3908/#3910, discussion #3390, xdna-driver #1645, FLM #636/#743, UG1079, Vitis, arXiv:2512.13282) | traces JSON + sha256 dans `evidence/urls/` | lecture directe, HTTP 200 (12/12) | ±contenu des pages GitHub tronquées (200 001 o) ; statut de merge de #743 non affiché |
| P-02 | idem | Décodage BD du design 512 (64 BD patchées) | `sha256_insts` dans `evidence/exp_*` | `import npu_preflight; bd_records(...)` (exit 0) | champs lus selon `BdLowering.cpp:285-322` ; unité de `word[0]` dépend du chemin |
| P-03 | idem | Garde-fou de dimensionnement | — | `python scripts/test_alloc_guard.py` → **12/12, exit 0** | 12 cas ne prouvent pas la sûreté d'une taille acceptée |
| P-04 | idem | Refus pré-vol design 512, B = 8 323 072 o | `sha256_insts` | `python scripts/npu_preflight.py --insts … --sizes 16777216,8323072,16777216` → **exit 3, refused=true** | `--sizes` est positionnel A,B,C |
| P-05 | idem | Acceptation pré-vol, B = 8 388 608 o | idem | `… --sizes 16777216,8388608,16777216` → **exit 0, PASS** | `arg1` porte `desaccord_descripteur=true` (lacune L-X-01) |
| P-06 | idem | Borne numérique de B (6 points) | `evidence/exp_O_*` | `python scripts/npu_gemm_ref.py --bo-map …` (exit 0/3) | une seule machine, un seul design |
| P-07 | idem | Empreinte réelle de C | `evidence/exp_N_footprint.json` | `python scripts/npu_footprint.py --sizes …` (exit 0) | écriture mesurée au mot, pas la sémantique |
| P-08 | idem | Faux PASS (même taille, sha identique à la sortie correcte) | `evidence/exp_P_order2.json` vs `exp_P_single_8372224.json` | `python -u scripts/npu_wrong_positions.py --bsizes …` (exit 3 / 0) | dépend de la mémoire adjacente (lacune L-X-02) |
| P-09 | idem | Oracle `xdna2-evidence-oracle` | — | `oracle.py --root audits/xdna2-overhead-20261018 ask "…"` (exit 0) | ne retrouve que nos propres rapports → pas une validation externe |
| P-10 | idem | RAG local | `rag_index.json` 686 Mo | `rag_bm25.search(...)` ×4 → **MemoryError** | échec non contourné : lacune L-X-05 |

## Sources primaires de code (clone local, lecture seule)

| Objet | Référence | Ce qui est prouvé |
|---|---|---|
| `BdLowering.cpp:285-322` | `E:/trixdna_test/repos_mlir_aie` | champs `word[0]`, `word[3..6]` du BD |
| `BdLowering.h:147-149,180-184` | idem | biais −1 sur stride et `iteration_size` |
| `AIEXDialect.cpp:72-73` | idem | `inputWrap[3] = iteration_size+1`, stride en granules de 4 o |
| `Kernels_main.json` (design) | `E:/trixdna_test/passthrough_min.prj` | args `opcode/instr/ninstr/bo0..bo4` |

## Règle de conservation

Aucune preuve supprimée : un résultat réfuté garde son fichier et reçoit une note datée dans le
rapport de mission. Les binaires lourds ne sont pas versionnés — seules leurs empreintes.
