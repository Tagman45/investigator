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
| P-11 | idem | **L-X-01 fermé** : conflit de bornes fail-closed | `sha256_insts` du design 512 | défaut : `python scripts/npu_preflight.py --insts … --sizes 16777216,8388608,16777216` → **exit 4, FAIL_BOUND_CONFLICT** ; avec `--allow-bound-conflict` → **exit 0, PASS_BOUND_CONFLICT_ASSUME** ; `scripts/test_alloc_guard.py` → **14/14, exit 0** | l'acceptation du conflit reste possible (acte explicite) — c'est voulu |
| P-12 | idem | **L-X-04 fermé** : mapping A/B par CONTENU | `evidence/exp_LX04_ab_map.json` (`sha_pattern`, `sha_xclbin`, `sha_insts`) | `python -u scripts/npu_ab_map.py --reps 1` → **exit 0** ; 3/3 `state=4` ; motif en bo1 → C varie **en colonne** (8192→65536), motif en bo0 → **en ligne**, témoin → 8192 partout ⇒ **bo0=A, bo1=B** | un seul design, une seule machine ; A et B de même taille (8 MiB) |
| P-13 | `p1-web-pdf-github-20261018` | `web_fetch.py` sur 4 URL réelles | JSON + corps dans `audits/p1-web-pdf-github-20261018/evidence/` | arxiv 200/41 309 o ; doi.org → `final_url` arxiv (redirection suivie) ; SPA AMD **200 sur page inexistante** ; API GitHub 200/6 065 o | `redirects[]` vide malgré la redirection (L-P1-12) ; 200 ≠ contenu (L-P1-01) |
| P-14 | idem | `pdf_extract.py` sur `STEEL_2607.09385.pdf` | sha256 `fb5120afcd1c4f2ffe52f16122c96431fef7b7514284c19bf2ae5e38943b8187`, 1 712 562 o | `python scripts/pdf_extract.py … --with-text --max-pages 6` → **exit 0**, `PDF_TEXT_OK`, 33 551 o de texte, « 22.8× » retrouvé 3× | **0 ligne de tableau** extraite (L-P1-02 confirmée) |
| P-15 | idem | `collect_github_data.py ROCm/FastFlowLM` **non authentifié** | `evidence/gh_fastflowlm.json` (3 688 964 o) | **exit 0**, `authenticated=false`, 6 endpoints 200, 100 issues, `error=None` | 403 **non reproduit** → chemin d'erreur non exercé (L-P1-04 reste À REVÉRIFIER) |

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
