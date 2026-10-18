# Journal Phase 0 / vérifications — 18/10/2026 (session 3)

Chaque ligne : commande (ou script) → code de sortie → preuve. Aucun dépôt modifié,
aucun commit, aucun push. Tous les runs NPU sont des sous-processus isolés.

| # | Heure | Commande | Exit | Preuve |
|---|---|---|---|---|
| 1 | 13:14:48 | `bash scripts/phase0_probe.sh` (bloc verbatim, `set +e`) | 0 | `evidence/phase0_env_20261018T131448.log` (10 sondes, 8× EXIT=0, `pip show pyxrt`=1) |
| 2 | 13:16:28 | `rag_service.py search` ×3 (phase5_atb / payload[6] / buffer hors bornes) | 0,0,0 | `evidence/rag_phase0_20261018T131628.log` |
| 3 | 13:17:06 | `oracle.py ask` ×2 (`--root` = dossier d'audit) | 0,0 | `evidence/oracle_20261018T131706.txt` (5 794 o) |
| 4 | ~13:20 | `ls` outputs REA + lecture `FLM-REA-REVERSE.md` | 0 | 24 entrées ; `flm-rea-evidence.json` **absent** |
| 5 | ~13:25 | `cp` insts + XOR 1 bit + `npu_preflight.py` (original / modifié), C=1 MiB | 0 / **3** | `evidence/pf_flux_modifie.txt` ; plancher sha256 **non transférable** |
| 6 | ~13:30 | `python -m py_compile scripts/*.py` | 0 | — |
| 7 | ~13:35 | `audit_preflight_order.py` v1 (arbre complet par module) | 3 | 9 « défauts » = **faux positifs** (double comptage module/fonction) |
| 8 | ~13:40 | `audit_preflight_order.py` v2 (module = code de 1er niveau) | 3 | 18 défauts dont appels à `main()` auto-protégé = faux positifs restants |
| 9 | ~13:45 | `audit_preflight_order.py` v3 (callee auto-protégé, `declare_scope`, garde interne, fichiers de test à part) | **0** | `evidence/exp_N_preflight_order.json` — `PASS_ORDRE_GLOBAL` |
| 10 | ~13:50 | `test_alloc_guard.py` (stub pyxrt, 7 cas) | **0** | 7/7 OK : refus sans pré-vol, refus à la source, mode borne, périmètre déclaré, `role=instr`, motif obligatoire |
| 11 | ~13:55 | `npu_gemm_ref.py --bo 7995392` (512) | 0 | `exp_P…json` → **FAIL_NUMERIQUE** 249 856/262 144 |
| 12 | ~13:58 | `npu_gemm_ref.py --bo 2097152` (512) | 2 | `exp_Q…log` → **pré-vol REFUSE** (A 2 Mio < 7 995 392) |
| 13 | ~14:05 | `--bo-map 16777216,7995392,7995392` (T3) | 0 | `exp_R…json` FAIL → ce n'est pas A |
| 14 | ~14:07 | `--bo-map 7995392,16777216,16777216` (T4) | 0 | `exp_S…json` PASS → A suffit |
| 15 | ~14:10 | `--bo-map 16777216,7995392,16777216` (T5) | 0 | `exp_T…json` **FAIL → B coupable** |
| 16 | ~14:12 | `--bo-map 16777216,16777216,7995392` (T6) | 0 | `exp_U…json` PASS → C hors de cause |
| 17 | ~14:18 | B = 8 388 608 / 10 485 760 / 12 582 912 (512) | 0,0,0 | `exp_V_gemm_B_{8388608,10485760,12582912}.json` PASS |
| 18 | ~14:25 | Planchers 512 ajoutés ; `--bo-map 7995392,7995392,7995392` | **3** | `exp_W_512_refus.log` : la config fausse est **refusée** |
| 19 | ~14:27 | Re-validation 16 Mio après correctif | 0 | `exp_X_512_16mio_revalide.json` PASS_NUMERIQUE |
| 20 | ~14:29 | B au plancher mesuré 8 388 608 | 0 | `exp_Y_512_B_plancher.json` PASS_NUMERIQUE |
| 21 | ~14:31 | `npu_preflight.py --insts insts_modifie_1bit.bin` | 0 | verdict **`PASS_NON_CERTIFIE`** (`design_certifie=false`) |

## Faits nouveaux (statut)

- **RÉFUTÉ** — « l'étendue descripteur est un majorant sûr » : B du design 512 échoue à
  7 995 392 o (prédiction 5 832 704 o), passe à 8 388 608 o (§6 du rapport principal).
- **SOURCE_CONFIRMED** — layout des mots de BD (`TxnEncoding.h` + commentaires
  `AIEDMATasksToNPU.cpp:591-629`) ; **UNKNOWN** — layout de word[6].
- **MESURÉ** — 4 occurrences de contournement du pré-vol par le wrapper ; corrigées.
- **RÉFUTÉ** — « l'oracle ne renvoie que des horodatages » (sortie complète exploitable).
- **RÉFUTÉ** — « le RAG remonte du hors-sujet » pour des requêtes **ciblées** projet.

## Incidents d'outillage (à ne pas refaire)

1. **`/tmp` MSYS ≠ `/tmp` Windows** : `cp` écrit dans `%TEMP%` (MSYS) tandis que le Python
   Windows résout `/tmp` en `C:\tmp` → le test de falsification a d'abord tourné sur le
   fichier **non modifié** (silencieusement). Utiliser des chemins Windows absolus des deux
   côtés. Détecté par un sha256 identique entre « original » et « modifié ».
2. **Garde-fou placé trop bas** dans `alloc()` : après `pyxrt.bo.flags`, le test négatif
   levait `AttributeError` au lieu du refus attendu → contrôle remonté en tête de fonction.
3. **Analyse AST naïve** : analyser l'arbre entier pour le pseudo-niveau « module »
   dupliquait les corps de fonction → 9 faux défauts. Mesuré, corrigé, documenté.

## Prochaine action

P1 : décoder word[6] (`AIEDmaToNpu.cpp`, émission `NpuWriteBdOp` + encodeurs ND) pour
remplacer la formule empirique `(payload[6]>>16)×0x10000` par les champs réels
(d0/d1/d2 sizes & strides, `iteration_size`) — suppression de la classe de faux PASS
démontrée §6.
