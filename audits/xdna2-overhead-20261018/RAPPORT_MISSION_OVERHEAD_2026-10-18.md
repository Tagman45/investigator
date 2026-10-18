# Mission XDNA2 — identifier et éliminer l'overhead runtime sur Windows

**Date** : 18/10/2026 · **Machine** : Nitro AN16S-61, Ryzen AI 9 365 (Radeon 880M)
**Statut global** : `TESTED` jusqu'à l'exécution NPU, **`BLOCKED` sur la justesse du résultat**
**Aucun commit, aucun push** · rapports antérieurs **non modifiés** (nouveau fichier uniquement)

## 1. Environnement réellement constaté (mesuré, pas supposé)

| Élément | Valeur | Commande |
|---|---|---|
| XRT | 2.21.0 (HEAD, hash `15e6319be8de…`) | `xrt-smi --version` (exit **0**) |
| Pilote NPU | 32.0.20101.3760 | idem |
| Firmware NPU | 1.1.2.64 | idem |
| Device | **NPU Strix** — BDF `[0065:00:01.1]` | `xrt-smi examine` (exit **0**) |
| pyxrt | présent (`miniconda3/Lib/site-packages/pyxrt.pyd`, Python 3.13.13) | `import pyxrt` |
| Chaîne AIE | `aiecc` (git `af819a802f4`), `xclbinutil.exe`, `aiebu-asm.exe` dans `C:/Xilinx/XRT` | `which`, `aiecc --version` |

Preuve brute : `evidence/probe_xrt.txt` (sha256 `1844ce1a…`).

## 2. Pourquoi le smoke XCLBIN n'avait pas été suivi d'une exécution NPU

Constat de départ : la preuve précédente s'arrêtait à la **compilation** (`aiecc` → `out.xclbin`).
Aucune **soumission** n'avait été tentée : le chemin hôte (`pyxrt` : device → xclbin →
`register_xclbin` → `hw_context` → `kernel` → `run.wait()`) n'avait jamais été appelé.
Ce n'est donc pas un outil manquant : c'est un **test non exécuté**. Il l'est maintenant.

## 3. Commandes exécutées, résultats bruts

| # | Commande | Exit | Résultat observé |
|---|---|---|---|
| 1 | `xrt-smi examine` | 0 | device `NPU Strix` présent |
| 2 | `scripts/npu_probe.py --xclbin <smoke out.xclbin>` | 3 | device/register/hw_context/kernel **OK** ; noyau `MLIR_AIE` ; soumission OK ; `run.wait()` → **`ERT_CMD_STATE_ERROR`** (design vide : `runtime_sequence` sans instruction) |
| 3 | `scripts/npu_probe.py --xclbin <phase5_atb_m32k64n128.xclbin> --no-run` | 0 | 8 arguments, noyau `MLIR_AIE`, `group_id(1)=…1`, données `…0` |
| 4 | `xclbinutil --dump-section EMBEDDED_METADATA:RAW:…` | 0 | signature : `opcode(u64), instr(char*), ninstr(u32), bo0..bo4` |
| 5 | `txn_t0.py <…_insts.bin>` | 0 | TXN 1292 mots : **136 ops**, 40 BLOCKWRITE + 40 DDR_PATCH (40/40 `seed==argplus`), BD len **32768 / 65536 / 16384** |
| 6 | matrice de flags BO | 0 | **seuls `cacheable` et `host_only` sont acceptés** ; les valeurs XCL `0x98` (EXECBUF) et `0x17` → `RuntimeError: unsupported buffer type` |
| 7 | `scripts/npu_run_txn.py --opcode 3 --flags cacheable` | 0 | **`ERT_CMD_STATE_COMPLETED`**, C réécrit (16320/16384 octets différents), BO @ `0x4018000/0x4020000/0x4030000` |
| 8 | `scripts/npu_gemm_verify.py --opcode 3` | 3 | exécution terminée mais **`C ≠ A·B`** (cos NaN, C quasi nul) |
| 9 | `scripts/npu_gemm_diag.py --opcodes 3,1` | 0 | voir §4 |

## 4. Diagnostic du résultat (ce que le NPU écrit réellement)

| Opcode | État matériel | C écrit ? | Contenu de C | cos vs `A·B` |
|---|---|---|---|---|
| **3 (TXN)** | `ERT_CMD_STATE_COMPLETED` | **oui** (16320/16384 octets écrasés, 64 octets intacts) | 7872/8192 **zéros**, `max_abs ≈ 3.12e38` (déchets), 0 NaN | **0.0057** |
| **1 (PMC)** | `ERT_CMD_STATE_COMPLETED` | **non** (marqueur 0xcdcd intact sur 8192/8192) | 0xcdcdcdcd pur | 0.0043 |

Lecture : **la soumission et la complétion fonctionnent** (le runtime XRT Windows accepte le TXN et
l'ERT rend `COMPLETED`), mais **les données ne sont pas le GEMM attendu**.
`opcode=3` déclenche un transfert dont le contenu est faux ; `opcode=1` ne transfère **rien** tout en
rendant `COMPLETED` — un `COMPLETED` n'est donc **pas** une preuve d'exécution correcte.

## 5. Coûts mesurés séparément (mission §8)

| Étape | Mesure (ms) | Remarque |
|---|---|---|
| chargement xclbin | 0.15 – 0.21 | local |
| `register_xclbin` | 0.006 – 0.008 | |
| `hw_context` | 3.46 – 4.68 | **dominant au setup** |
| ouverture noyau | 0.06 – 0.12 | |
| allocation BO | 0.008 – 0.077 | |
| écriture + `sync TO_DEVICE` | 0.002 – 0.007 | |
| **SOUMISSION** | **0.10 – 0.21** | boucle chaude |
| **attente / exécution** | **2.18 – 2.35** | 10× la soumission |
| `sync FROM_DEVICE` | 0.09 – 0.26 | |
| premier `read()` après allocation fraîche | **85.7** | outlier (défaut de page / vidage cache), pas une constante |

## 6. Premier point non validé (blocage exact)

> **Chemin** : Windows → pilote → XRT → chargement XCLBIN → **soumission OK** → **exécution `COMPLETED`** →
> **vérification du résultat : ÉCHEC**.
> Blocage = sémantique des **BD patchés** (`DDR_PATCH`/`argplus`) : les adresses de BO observées
> (`0x4018000`, `0x4020000`, `0x4030000` en `cacheable` ; `0x13000`/`0x14000` en `host_only`)
> doivent être confrontées aux `argplus` du TXN. Le TXN a été produit pour une autre base d'adressage.

Ce point est identique, en substance, au blocage déjà consigné les 30/07 et 11/08 — mais il est
désormais **reproduit par un chemin hôte neuf (pyxrt)** et **chiffré** (états, timings, octets).

## 7. Prochaine action technique (proposée, non exécutée)

1. **Tester un kernel réel** : `C:/Program Files/flm/xclbins/DeepSeek-R1-0528-Qwen3-8B-NPU2/mm.xclbin`
   (512 220 o) avec son flux d'instructions capturé — c'est la cible « kernel réel FLM ».
2. **Confronter les adresses** : recalculer chaque `argplus` du TXN contre `bo.address()` obtenu ici,
   et comparer avec la base utilisée par FLM (`dyn_dispatch_core.dll`).
3. **Utiliser FLM comme oracle** : exécuter le même mm.xclbin via FLM officiel et tracer la soumission.
4. Ne déclarer `PASS` qu'après obtention d'un `C` conforme (cos > 0.99) sur entrées bf16 connues.

## 8. Registre des statuts

| Affirmation | Statut |
|---|---|
| Device NPU détecté par XRT Windows, xclbin chargeable, contexte et noyau créés | **TESTED** (`evidence/probe_*.txt/json`) |
| Soumission d'un run et complétion ERT (`COMPLETED`) | **TESTED** (`evidence/run_txn_op3_cacheable.json`) |
| Transfert de données vers C déclenché par `opcode=3` | **TESTED** (marqueur 0xcdcd écrasé) |
| Aucun transfert avec `opcode=1` | **TESTED** (marqueur intact 8192/8192) |
| Le NPU calcule le GEMM attendu **pour ce design** (`phase5_atb_m32k64n128`) | **REFUTED** (cos ≈ 0.006, C majoritairement nul) |
| Overhead runtime : soumission ≈ 0.1–0.2 ms, exécution ≈ 2.2–2.35 ms | **TESTED** (mesures ci-dessus) |
| Chaîne FLM `mm.xclbin` sur ce chemin pyxrt | **NOT TESTED** |
| Gain de performance (t/s) par élimination d'overhead | **UNKNOWN** — aucune mesure de débit |
| Cause racine du résultat faux (offset/seed/additif) | **HYPOTHESIS** — à démontrer |

## 9. Artefacts et hashes (sha256 — vérifiables : `sha256sum evidence/*`)

| Fichier | sha256 (intégral) |
|---|---|
| `evidence/bo_flags_matrix.txt` | `5391a3774bc99b863d4867fcf69b879b8621e3dbf70b2f77b75d6abfde5c46b6` |
| `evidence/gemm_diag.json` | `7db87f1894ee9149a012e9e896ba5a759d12b6134d42a3ca014d733776f3f6e9` |
| `evidence/gemm_diag.txt` | `a1d4abbf4d1c937267a7e057baffe0b12833b63589c99c691dda5733ac3334cd` |
| `evidence/gemm_verify_op3.json` | `5bd468bccb2ee4e44fb82b9045041c43b50dfd33657790f88aaca5d9897ee503` |
| `evidence/gemm_verify_op3.txt` | `0c47cf6e6ee327e28167a09ade2b8e0d425ce2cd06fe10261d6e816151a94db4` |
| `evidence/phase5_metadata.xml` | `54bdb13ea286d097d13a3f4a3dd29fc0cb29a8a78797842a0fd805177625f896` |
| `evidence/phase5_xclbin_info.txt` | `5135f778f0f963e4ce6f1709beb4138da03172a100d5fde9e4a4430631edca13` |
| `evidence/probe_phase5_xclbin.json` | `556cab339120f9226cf3f4ad97def0ef1b72772b84d0208afc497efc2cc7bc4c` |
| `evidence/probe_phase5_xclbin.txt` | `8b8e46ec1b4856c212fd56b6f5d31ebf2637d53d843f63be353f68537f296d61` |
| `evidence/probe_smoke_xclbin.json` | `fee3e1692510c57914fce718f5ecd6942256692faa963c91a9a04d82287b5d06` |
| `evidence/probe_smoke_xclbin.txt` | `018394a29cf3a6003216a9a16541b670aa3c2551b3490a47f2881e93975d5b34` |
| `evidence/probe_xrt.txt` | `1844ce1a99a945b2e0c5007563391063e0ca38f41eb1eb3b684ec9bc009b1da3` |
| `evidence/run_txn_op3.txt` | `33f2d73ddd0597cb7a69b322278e65a214808c9137f08ac1a2bd15df885f5eec` |
| `evidence/run_txn_op3_cacheable.json` | `a6e527d499e7bdce5d782bcb43f29ebc13dc216d5b1df46fa0df1ea600cc14cd` |
| `evidence/run_txn_op3_cacheable.txt` | `c34cde014355ca867c5595078d7944af315bdd3bc9728881f27be9e6544af6a0` |
| `evidence/txn_t0_phase5_insts.txt` | `35c8668aee48ecdd6e57b8ea5da4be586a1b03dc5213c2e69e835a55c2bb9063` |
| `evidence/patch_probe_op3.txt` (run BO dimensionnés, 2,685 ms) | `9807a0d5a55442dbd84a3a2d8860b17c2639b39d0883a67a9e2a3a8905a9a108` |
| `evidence/patch_probe_op3.json` (run 1, 2,398 ms — même sonde, exécution distincte) | `1dc009f8c2028b2be7170afd86616e4773cadf1d3dd819b0ea144805c54fae77` |

## 10. Limites

- Un seul design testé (`phase5_atb_m32k64n128`), un seul jeu de tailles de BO ; les formes M/K/N sont
  **déduites** des tailles de BD (64×256×128), pas lues dans un manifeste.
- Aucune mesure de débit (t/s), aucun test du kernel `mm.xclbin`, aucun profiling XRT.
- Les timings sont des mesures d'horloge murale Python ; la variance n'a pas été caractérisée (n=1).

## 11. Croisement avec les rapports du projet (relus le 18/10/2026)

Fichiers relus : `C:/Users/videl/Desktop/xdna2-project/` → `RAPPORT_EXHAUSTIF.md` (12/07),
`VERDICT_HONNETE.md` (10/07), `RAPPORT_FINAL_XRT_PIPELINE.md` (09/07),
`AUDIT_ARCHITECTURE_RUNTIME.md` (09/07), `LISTE_PROBLEMES.md` (09/07) ;
et `E:/trixdna_test/phase5_atb/hrx_run.log` (11/08, 3073 o).

| Constat de ce rapport | Ce que disent les documents du projet | Verdict du croisement |
|---|---|---|
| Soumission **0.10–0.21 ms** (100–210 µs) | « plancher dispatch 67 µs (`xrt-smi validate`) ; 72 µs (destevez) » — RAPPORT_EXHAUSTIF §2.1 | **COMPATIBLE** — même ordre de grandeur ; l'écart (+30 à +140 µs) est cohérent avec un harnais Python et une horloge murale |
| Exécution **2.18–2.35 ms** | HRX `dispatch wall_ms=4.142` (hrx_run.log) ; NPU compute ~5 ms/token (RAPPORT_EXHAUSTIF §2.1) | **COMPATIBLE** — ordre du milliseconde ; harnais et périmètre différents |
| `opcode=3` → `ERT_CMD_STATE_COMPLETED` | « opcode=3 = TXN AIE2 (state=8) » (RAPPORT_EXHAUSTIF §4.8) ; « opcode=3 cassé par driver 26/07 + XRT 1.8.0 » (AGENTS.md, Claims Confirmés #22) | **DIFFÉRENT** — ici XRT **2.21.0** → `COMPLETED`. Cause = version de pile (HYPOTHESIS, non tranchée) |
| `opcode=1` → `COMPLETED` **sans aucun transfert** | « opcode=1 = PMC fonctionnel (state=4, 2037 ms) » (RAPPORT_EXHAUSTIF §4.8) ; « state=4 mais SHIM DMA non déclenché » (AGENTS.md #23) | **CONFIRME #23**, **INFIRME** la lecture « fonctionnel » |
| GEMM faux : `cos ≈ 0.006`, 7872/8192 zéros | `hrx_run.log` (même design : `phase5_atb_m32k64n128_insts.bin`, 5168 o = 1292 mots) : `checked=262144 wrong=262144` → `FAIL` | **MÊME ISSUE (échec)**, mais **non corroborant** : `nonzero_expected=0` = référence nulle (contrôle dégénéré) et `checked=262144` ne correspond pas aux **8192** sorties de ce design — log à re-jouer, inutilisable comme preuve |
| « GEMM BF16 validé, C=K=8192, 262144 corrects » (AGENTS.md l.1399 / Claims #20) | porte sur `phase5_bf16_512x8192x512.{xclbin,insts}`, **artefact différent** de celui testé ici | **NON COMPARABLE** — la validité de #20 reste non vérifiée, mais elle n'est **pas** contredite par ce rapport |
| « BOs modifiés ≠ preuve de calcul correct » (VERDICT_HONNETE §3) | identique | **CONFIRME** — ce rapport fournit le test manquant, et il échoue |

**Trace dans le dossier projet** : aucun. Les `.md` du dossier n'ont pas été modifiés le 18/10
(derniers : `README.md` 14/10 09:40, `ARBORESCENCE_RUNTIME.md` 14/10 08:10). Ce livrable vit dans
`skills-audit-reports/audits/xdna2-overhead-20261018/` ; aucun rapport antérieur n'a été touché.

## 12. CORRECTIONS [18/10/2026, session 2] — preuves : `JOURNAL_EXPERIMENTAL_2026-10-18.md`

Le texte des §1–§11 est **conservé tel quel** (règle projet : corriger avec preuve + date, jamais
supprimer). Les points suivants sont révisés par des tests exécutés après la rédaction.

1. **[CORRIGÉ 18/10/2026] §4 et §6 : « 8 tuiles de 16 Kio attendues dans C » est FAUX.**
   Les mots BD portent des descripteurs **3D** (`0x04000000` ⇒ stride `0x400` ; `D0/D1/D2
   size/stride`, `Inferred D2 size` côté `gemm.dll`). Une BD de `buffer_length = 16 384` couvre
   **64 × 256 o espacés de 1 024 o** ; les 8 BD de C couvrent **1 MiB**. Preuve directe : avec
   C = 2 Mio, **262 144 mots** modifiés contigus (`exp_D_map_c2M.json`).
2. **[CORRIGÉ 18/10/2026] §6 : la cause du résultat faux est le DIMENSIONNEMENT DES BUFFERS.**
   `B = 851 968` (valeur « exacte » déduite des `arg_plus`) est **insuffisant** : le NPU lit
   au-delà de l'allocation, la mémoire lue varie, C devient non déterministe. Isolation :
   `B ∈ {851968, 917504, 1048576}` → non reproductible ; `B = 2 097 152` → **sha256 identique sur
   deux runs**. A (1 998 848) est suffisant ; C doit être ≥ 1 MiB.
   Méthode fautive à ne plus employer : dimensionner sur `max(arg_plus) + buffer_length`.
3. **[CORRIGÉ 18/10/2026] §2/§9 : `COMPLETED` + DMA ≠ calcul.** Contrôle négatif opcode 1 :
   `COMPLETED` avec **0 octet transféré** (`exp_neg_opcode1_map.json`). Le statut ERT ne prouve
   que l'acceptation des commandes.
4. **[CORRIGÉ 18/10/2026] §6 : « sémantique des patches inconnue » → établie.**
   `arg_plus := 0x1000` décale toute l'empreinte de **+4 096 octets** ; `arg_plus := 0` la ramène à
   l'origine. Les patches sont **appliqués, linéaires au byte** (`exp_C_patch0/patchsent`).
   Corollaire : l'hypothèse « patches ignorés » est **réfutée**.
5. **[CORRIGÉ 18/10/2026] §6/§7 : le fold `0x80000000` n'est PAS la solution.** Appliqué, il donne
   `COMPLETED` et **0 octet écrit** : cette pile n'attend pas l'adresse dans l'ouverture DDR AIE
   (`exp_C_patchfold_run1.json`).
6. **[CORRIGÉ 18/10/2026] §10 : « SIGSEGV quand les BO dépassent ~0,5 Mo » est FAUX.**
   Matrice par processus : 16 Kio plante comme 544 Kio (exit 139) ; avec destruction explicite des
   BO, exit **0** dans tous les cas. Cause = **ordre de destruction**, taille non pertinente. Autre
   défaut isolé : `pyxrt.bo(..., group_id=0)` plante immédiatement → utiliser `kernel.group_id(n)`.
7. **[CORRIGÉ 18/10/2026] §4 : les statistiques de C du matin (`max_abs≈3,1e38`, 7 872 zéros,
   cos≈0,006) provenaient d'écritures HORS allocation** et ne décrivent pas le design. Elles sont
   conservées comme trace, mais **ne doivent plus être citées comme caractérisation du calcul**.
8. **[NOUVEAU 18/10/2026] §7 : `mm.xclbin` est ABI-compatible mais NON exécutable en l'état.**
   Même signature (`MLIR_AIE`, 8 args, `dpu_kernel_id=0x901`), **aucun flux d'instructions pour ce
   xclbin** dans `C:/Program Files/flm` ; le TXN est généré au runtime par `gemm.dll` (assembleur TXN
   + contrôles d'alignement M/K/N). Statut : **NOT TESTED**, premier prérequis = capturer ce flux.
   **[PRÉCISÉ 18/10/2026, session 2]** des dumps de ctrlcode existent ailleurs sur disque : famille
   `full_txn.bin` en `devgen=1`/`cols=4` (walk incohérent), `generated_sequence.bin` et
   `flm_gemm_sequence.bin` = préambules. Le seul ctrlcode **NPU2** cohérent disponible
   (`tools_ctrlcodes/generated_phase5_ctrl.bin`) a été **soumis et rejeté** : `ERT_CMD_STATE_TIMEOUT`,
   0 octet, deux runs (`exp_F_ctrlcode_run1/2.json`). Le ctrlcode est donc **lié à la topologie** du
   xclbin ; l'alternative « réutiliser un ctrlcode existant pour `mm.xclbin` » est **réfutée**.

Détail complet des commandes, codes de sortie et empreintes : `JOURNAL_EXPERIMENTAL_2026-10-18.md`.
Synthèse et prochaine expérience : `RAPPORT_TESTS_ABCDE_2026-10-18.md`.

---

## MISE À JOUR 18/10/2026 (soir) — garde-fou, borne de C, débit

Trois travaux ajoutés après ce rapport ; détail et preuves dans
`RAPPORT_GARDE_FOU_BORNE_C_DEBIT_2026-10-18.md` :

1. **Pré-vol de dimensionnement** : `scripts/npu_preflight.py` (étendue calculée depuis
   les descripteurs, refus exit 3 **avant allocation**) est désormais appelé par tous les
   scripts NPU du dossier ; `--allow-undersized` est réservé aux expériences de borne.
2. **Bornage de C** : la prédiction 1 590 016 o fondée sur les descripteurs est
   **RÉFUTÉE** — C sature à 1 048 576 o (1 048 064 perd 128 mots). Le pas `0x10000`
   n'est valable que pour l'argument 1 ; `descriptor_bounds.py` porte la correction et
   conserve l'ancienne valeur comme `ancienne_valeur`.
3. **Débit boucle chaude** (30 soumissions, `exp_K_gemm_loop.json`) : 1,281 ms médian par
   GEMM 512×8192×512 = 3,35 TFLOP/s, soit **5,685 %** du pic 58,98 TOPS (théorique 72,8 µs) ;
   262 144/262 144 valeurs correctes. Relecture d'un BO de 16 Mio : ~1 s (17 Mo/s).

### Suite 18/10 (soir) — B bisecté et recouvrement mesuré

4. **Borne de B resserrée** : minimum **1 966 080 o**, plus grand échec 1 949 696 o
   (8 répétitions par point). À 3 répétitions, 1 933 312 o paraissait suffisant — il
   échoue à 8. Sous la borne, B est **lu hors bornes** : C devient faux et instable sans
   aucune erreur visible (`n_changed(B)=0` partout, empreinte de C constante).
5. **Recouvrement** (`npu_gemm_loop.py --depth`) : 1,301 ms/run à profondeur 1, 1,161 ms à
   profondeur 4 → **+10,8 % seulement**, sha256 de C identique aux trois profondeurs.
   Le limiteur de débit est le design, pas la file de soumission.

---

## SESSION 3 — Phase 0 fiable et réfutation de la règle de dimensionnement

Rapport détaillé : `AUDIT_PHASE0_ET_VERDICTS_2026-10-18.md` · journal horodaté :
`JOURNAL_PHASE0_2026-10-18.md`.

1. **Phase 0 fiable** : 10 sondes d'environnement avec code de sortie par outil
   (`evidence/phase0_env_20261018T131448.log`) — `xrt-smi examine` **fonctionne** (device
   `[0065:00:01.1] NPU Strix`), `xclbinutil` et `aiecc` (`af819a802f4`) disponibles,
   `pyxrt` importé depuis `miniconda3\Lib\site-packages\pyxrt.pyd`, `pip show pyxrt` = 1
   (le .pyd ne vient pas de pip).
2. **Skills, oracle, RAG** : 9 fiches lues ; oracle exécuté avec **sortie intégrale**
   (5 794 o) ; RAG relancé avec des requêtes projet → **plus de hors-sujet Snapdragon/HTP**.
3. **RÉFUTATION MAJEURE** : sur `phase5_bf16_512x8192x512`, B échoue à 7 995 392 o alors que
   l'étendue prédite n'est que de 5 832 704 o → la règle **laisse passer des données fausses**
   (249 856/262 144 correctes, ERT `COMPLETED`). Le « PASS » précédent à 16 Mio autorisait
   l'allocation sans certifier le résultat.
4. **Correctifs** : planchers mesurés par `sha256(insts)` (7 995 392 / 8 388 608), verdict
   `PASS_NON_CERTIFIE` sans plancher, contrôle **dans** le wrapper d'allocation,
   `role="instr"` hors contrat, `declare_scope('<motif>')` journalisé. Non-régression :
   16 Mio toujours `PASS_NUMERIQUE`, B=8 388 608 `PASS_NUMERIQUE`, config fausse **refusée
   exit 3**, 7/7 tests négatifs, audit AST `PASS_ORDRE_GLOBAL`.
