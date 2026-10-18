# Phase 0 fiable, vérdicts et réfutation d'une règle — 18/10/2026 (session 3)

Machine : Acer Nitro AN16S-61 · Ryzen AI 9 365 · NPU `DEV_17F0` · Windows 11 26200.9711
XRT 2.21.0 (`15e6319be8de…`) · pilote 32.0.20101.3760 · firmware 1.1.2.64 · Python 3.13.13.
Aucun dépôt modifié. **0 commit, 0 push** (état Git en §9).

Statuts utilisés : FACT · SOURCE_CONFIRMED · MESURÉ · DÉRIVÉ · HYPOTHÈSE · RÉFUTÉ ·
INCONCLUSIF · NON TESTÉ.

---

## 1. Phase 0 — environnement sondé, un code de sortie par outil

Bloc exécuté verbatim (`scripts/phase0_probe.sh`, `set +e`, aucun pipe masquant),
journal intégral : `evidence/phase0_env_20261018T131448.log`.

| Sonde | Résultat | Exit |
|---|---|---|
| `python --version` | Python 3.13.13 | 0 |
| `xrt-smi --version` | XRT 2.21.0 · pilote 32.0.20101.3760 · FW 1.1.2.64 | 0 |
| `xrt-smi examine` | **supporté** : modèle Nitro AN16S-61, 20 cœurs, 32 041 Mo, device présent `[0065:00:01.1] NPU Strix` | 0 |
| `xclbinutil --help` | présent dans le PATH | 0 |
| `aiecc --version` | `git SHA af819a802f4`, compilé 28/08/2026 | 0 |
| `git --version` | 2.55.0.windows.3 | 0 |
| `sha256sum --version` | GNU coreutils 8.32 | 0 |
| `import pyxrt` | OK, `pyxrt_file= C:\Users\videl\miniconda3\Lib\site-packages\pyxrt.pyd` | 0 |
| `pip show pyxrt` | **package introuvable** — `pyxrt` est un `.pyd` livré par XRT, pas un paquet pip (constat, pas un défaut) | 1 |
| `git rev-parse` / `status` | racine `C:/Users/videl/skills-audit-reports` | 0 / 0 |

Cinq critères de passage Phase 0 :

| Critère | État |
|---|---|
| Versions + codes de sortie enregistrés | ✅ §1 |
| `pyxrt` importé, chemin réel consigné | ✅ |
| Les 8 skills de la checklist localisés **et lus** | ✅ §2 (9 fiches lues : les 8 + `evidence`) |
| Réponse **complète** de l'oracle enregistrée | ✅ §3 (5 794 o, contenu exploitable, `EXIT_Q1=0`, `EXIT_Q2=0`) |
| Recherche RAG répétée, ciblée, hors-sujet écarté | ✅ §4 |
| Répertoire de rapports localisé depuis le FS | ✅ §5 (une seule copie trouvée) |

---

## 2. Skills — règles et limites effectivement imposées

| Skill (chemin `.config/opencode/skills/…`) | Règle imposée (§) | Limite déclarée (§) |
|---|---|---|
| `evidence` (57 l.) | tout énoncé porte un statut + preuve ; corriger, jamais supprimer | — |
| `oracle-query` (83 l.) | **une seule** source par question, réponse ≤ 5 lignes | ne remplace pas une mesure |
| `xdna2-evidence-oracle` (74 l.) | 3 niveaux SOURCE / HYPOTHESIS / PROOF ; ne jamais inventer une trace | **pas d'exécution NPU** ; HTTP 200 ≠ preuve |
| `xdna2-cross-audit` (62 l.) | matrice affirmation → preuve → source externe → statut → expérience manquante ; ne jamais confondre les natures de débit | n'exécute pas les collectes ; RAG en lecture seule |
| `xdna2-path-explorer` (105 l.) | statuts séparés OBSERVED / SOURCE_CONFIRMED / INFERRED / HYPOTHESIS / UNKNOWN ; dry-run par défaut | « l'explorer ne valide pas le matériel seul » |
| `aie2p-hand-asm-debug` (157 l.) | jamais « corrigé » sans A/B ; jamais « cause racine » sans 2 tests convergents | « max 6 instructions/bundle » non revérifié = UNKNOWN |
| `git-ecosystem-investigator` (226 l.) | vérification Internet obligatoire, statuts calculés (CONFIRMED…UNVERIFIED), `UNVERIFIED ≠ INEXISTANT` | un graphe n'est pas une preuve d'exécution |
| `search-policy` (56 l.) | ordre cache → Graft → BM25 → rgx ; **jamais `rg` direct** ; jamais de scan de `E:\trixdna_test` | — |
| `debug-method` (62 l.) | repro → hypothèses → test discriminant ; préférer le test qui élimine plusieurs hypothèses | ne rien modifier avant repro + hypothèse |

---

## 3. Oracle / REA — réponse intégrale, statut tranché

- Oracle `xdna2-evidence-oracle` exécuté sur ce dossier d'audit, **sortie intégrale**
  conservée (`evidence/oracle_20261018T131706.txt`, 5 794 o, `EXIT_Q1=0`, `EXIT_Q2=0`) :
  chemins + scores + titres de sections, donc exploitable — l'« horodatage seul » du tour
  précédent est **RÉFUTÉ** comme état actuel.
- L'oracle a lui-même remonté la pièce décisive du dossier : `ANNEXE_REVERSE_AXES_2026-10-18.md`
  (§2 « Axe BD / arg_plus — FACT, source primaire », §3 « Axe tailles de buffers »).
- REA : dossier `C:\Users\videl\Documents\Codex\2026-10-15\…-rea-https\outputs\` **inventorié**
  (24 entrées) et `FLM-REA-REVERSE.md` **lu intégralement** (7 544 o) : `flm.exe` PE x86-64
  6 778 368 o, sha256 `0b1385d0…5d534`, snapshot Ghidra (13 113 procédures, 6 414 chaînes),
  239 xclbin inventoriés par `xclbinutil` (0 erreur), imports `XRT_COREUTIL.DLL`
  (`xrt::device`, `xrt::bo`, `xrt::hw_context`), device `VEN_1022&DEV_17F0`, `oem67.inf`
  32.00.20101.3760 — **cohérent avec la sonde §1**.
- **Régression de provenance à consigner** : `outputs/flm-rea-evidence.json`, lu lors d'une
  session antérieure, **n'existe plus** (`FILE_DOES_NOT_EXIST` le 18/10). Les faits REA
  cités ci-dessus proviennent donc de `FLM-REA-REVERSE.md` et des inventaires, pas de ce JSON.

---

## 4. RAG — recherche ciblée relancée

3 requêtes ciblées, `rag_service.py` (lecture seule), journal
`evidence/rag_phase0_20261018T131628.log` — **3 × EXIT=0**.

| Requête | Meilleur résultat (score) | Pertinence |
|---|---|---|
| phase5_atb … descripteur BD buffer_length ctrlcode | `docs/ANALYSE_EXHAUSTIVE_DMA_IRON_09_08.md` (17,94) | pertinent |
| payload[6] iteration stride buffer_length BD format | `docs/RAPPORT_REVERSE_COMPLET.md` (22,89) — « Format BD Descriptor (32 bytes) » | pertinent |
| taille buffer B hors bornes ERT COMPLETED données fausses | `docs/SESSION_04_08_ELF_COMPLET…md` (18,85) — états ERT | pertinent |

Le hors-sujet Snapdragon/HTP signalé au tour précédent **n'apparaît plus** : les requêtes
ont été reformulées avec le vocabulaire exact du projet (`phase5_atb`, `payload[6]`,
`ERT COMPLETED`). Verdict du tour précédent : **RÉFUTÉ pour la formulation actuelle**,
**CONFIRMÉ pour la formulation générique** (une requête « descripteurs XDNA2 » seule reste
ambigüe et remonte du matériel Qualcomm — à éviter).

---

## 5. Trois lacunes les plus graves (critère : provoquer un faux résultat ou masquer un coût)

1. **LACUNE 1 — le pré-vol pouvait laisser passer une configuration qui produit des données
   fausses.** C'est la plus grave : elle inverse la garantie annoncée au tour précédent.
2. **LACUNE 2 — le pré-vol était contournable par le chemin d'allocation** (le wrapper
   `alloc()` ne vérifiait rien ; 4 occurrences détectées : `npu_exp.py:170/203/345/418`).
3. **LACUNE 3 — « empreinte d'écriture complète » ≠ « résultat correct »** : sur le design
   512, une configuration sous-dimensionnée donne **249 856/262 144 (95,3 %) valeurs
   correctes**, ERT `COMPLETED`, sha instable — un contrôle par hash ne suffit pas.

---

## 6. LACUNE 1 — test discriminants : la règle de dimensionnement est RÉFUTÉE

Hypothèse testée : « l'étendue calculée depuis les descripteurs est un majorant sûr de la
taille réellement nécessaire ».

Protocole : design `phase5_bf16_512x8192x512` (insts `487fa1ff…`, xclbin `ba93cb73…`),
`npu_gemm_ref.py --bo-map A,B,C` — **une seule variable à la fois**, référence numérique
262 144 valeurs = 8192.0, 2 répétitions, `--json evidence/exp_{P,Q,R,S,T,U,V,W,X,Y}*.json`.

| Test | A | B | C | Résultat | Verdict |
|---|---:|---:|---:|---|---|
| étendues prédites partout | 7 995 392 | 7 995 392 | 7 995 392 | 249 856 correctes · 12 288 fausses · 8 704 NaN · sha instable | **FAIL_NUMERIQUE** |
| A isolé (T3) | 16 777 216 | 7 995 392 | 7 995 392 | idem FAIL | FAIL |
| **B isolé (T5)** | 16 777 216 | **7 995 392** | 16 777 216 | 249 856 correctes | **FAIL → B coupable** |
| C isolé (T6) | 16 777 216 | 16 777 216 | 7 995 392 | 262 144 correctes, sha stable | PASS |
| A isolé (T4) | 7 995 392 | 16 777 216 | 16 777 216 | 262 144 correctes, sha stable | PASS |
| B = 8 388 608 | 16 777 216 | 8 388 608 | 16 777 216 | 262 144 correctes, sha stable | **PASS** |
| B = 10 / 12 / 16 Mio | 16 777 216 | … | 16 777 216 | PASS 2/2 à chaque point | PASS |

**Verdict : RÉFUTÉ.** Sur ce design, B exige **> 7 995 392 o** et **≤ 8 388 608 o**, alors
que la règle prédisait **5 832 704 o** → sous-estimation d'au moins **2 162 688 o (37 %)**
dans le **sens dangereux** : la règle autorise une allocation qui produit des données fausses
sans aucune erreur visible. Le contrôle précédent (« PASS aux 16 Mio ») était un **faux
PASS** : il autorisait l'allocation, il ne certifiait pas le résultat.

**Cause du défaut de règle (SOURCE_CONFIRMED + UNKNOWN)** : `TxnEncoding.h` (en-tête
« single in-tree source of truth for the instruction format ») encode BLOCKWRITE comme
`opcode, (col|row<<8), addr, (4+count)*4, payload…` — le `payload` est le **contenu brut des
mots de BD**, et `AIEDMATasksToNPU.cpp:591-629` attribue word[0]=buffer_length,
word[1]=buffer_offset, word[2]=packet/enable, word[4]=burst_length[31:30]+d1_*,
word[5]=AXCache[27:24]+d2_*, word[7]=next_bd/use_next_bd/valid_bd/locks. **Aucun mot ne
porte de pas `0x10000`** : `(payload[6] >> 16) × 0x10000` était un ajustement empirique
présenté à tort comme un décodage. Le layout exact de word[6] (champs d'itération) reste
**UNKNOWN**.

## 7. Correctifs appliqués et tests de non-régression

| Correctif | Fichier | Preuve |
|---|---|---|
| Planchers mesurés du design 512 (`arg0 ≥ 7 995 392`, `arg1 ≥ 8 388 608`), indexés par sha256 d'insts | `npu_preflight.py` | `--insts 487fa1ff…` → PASS ; `7995392` partout → **REFUS exit 3** (config mauvaise bloquée) |
| Verdict `PASS_NON_CERTIFIE` + avertissement explicite quand aucun plancher n'existe | `npu_preflight.py` | flux modifié 1 bit → `design_certifie=false`, `PASS_NON_CERTIFIE`, exit 0 |
| Pré-vol déplacé **avant la 1re allocation** (BO d'instructions inclus) dans `cmd_sensitivity` | `npu_exp.py` | audit AST : `pre_vol=[…]` avant déclencheur |
| Garde-fou **dans le wrapper** `alloc()` : refus sans contexte de pré-vol ; refus à la source si `size < cible` ; `role="instr"` hors contrat ; `declare_scope('<motif>')` pour les blocs hors contrat | `npu_exp.py` (+ `npu_gemm_ref/loop`, `npu_dump_c`, `npu_readsem`) | `scripts/test_alloc_guard.py` → **7/7 OK, exit 0** |
| Audit statique d'ordre (AST, appels indirects, alias d'API, fichiers de test comptés à part) | `scripts/audit_preflight_order.py` | **`PASS_ORDRE_GLOBAL`, exit 0** (0 défaut production, 2 défauts attendus dans le fichier de test) |
| Faux positifs corrigés (module analysé sur le code de premier niveau ; callee auto-protégé) | `audit_preflight_order.py` | 18 → 2 défauts, tous deux dans `test_alloc_guard.py` (cas de refus volontaires) |

Non-régression : `16 Mio` reste `PASS_NUMERIQUE` (`exp_X`), `B = 8 388 608` passe (`exp_Y`),
tous les scripts compilent (`python -m py_compile scripts/*.py`).

Falsification du contournement : `npu_exp.alloc()` sans pré-vol → `UnscopedAllocationError`
(T1) ; plancher sha256 non transférable — flux identique à 1 bit près
(`0a3d03e9…` vs `3a2e66bf…`) : original `EXIT_ORIGINAL=0`, modifié **`EXIT_MODIFIE=3`**.

---

## 8. Croisement avec la littérature — ce qui transfère, ce qui ne transfère pas

| Source | Affirmation | Notre état | Transfert |
|---|---|---|---|
| MLIR-AIE **#3910** (Full-ELF Windows, `xrt::bo&` dans `set_arg`, pilote 3761) | chemin Full-ELF validé sur Windows | nous utilisons **xclbin + TXN** (`opcode=3`), pas Full-ELF ; notre pilote = **3760**, pas 3761 | **NON TESTÉ localement** — à ne pas reprendre tel quel ; la correction `xrt::bo&` ne nous concerne que si l'on passe en Full-ELF |
| MLIR-AIE **#3653** (BO hôtes créés avec `group_id=0` → `COMPLETED` + données fausses) | défaut de **groupe mémoire** | nos BO utilisent `kern.group_id(1)/(3,4,5)` ≠ 0, valeurs propres à chaque xclbin (`0x7B0001` atb, `0xED0001` 512) ; la cause de nos données fausses est **isolée sur la taille de B** (T5/T6) | **RÉFUTÉ comme cause de notre cas** ; reste un contrôle de premier ordre à automatiser (voir §11 P4) |
| MLIR-AIE **#3840** (mot word0 du MemTile col0 → `0x00CD0CD0`) | anomalie XDNA2 | nos A/B/C sont des BO DDR lus/écrits par DMA ; le motif d'échec observé est NaN/1e31 (lecture hors bornes), pas un mot isolé | **NON TESTÉ** — piste distincte, testable en cherchant `0x00CD0CD0` dans les sorties C archivées |
| MLIR-AIE **#3222** (séquences TXN dynamiques ; le polling peut annuler le gain) | coût CPU de construction + attente | notre mesure : soumission 0,061 ms vs attente ≈ 1,22 ms (95 % du temps d'un GEMM 512×8192×512) ; profondeur 1→4 : **+10,8 %** seulement | **COHÉRENT** : l'attente domine, le recouvrement ne suffit pas — confirme leur avertissement sur les fences |
| MLIR-AIE **#3908** (parallélisme MLIR désactivé dans le wheel épinglé) | compilation séquentielle | `aiecc` local = `af819a802f4` (28/08/2026) ; aucun temps de compilation mesuré ici | **NON TESTÉ** (aucune revendication) |
| MLIR-AIE **#3033** (débordement de longueur BD sur très grandes tailles) | bug de compilation, corrigé 05/2026 | nos BD portent `buffer_length` ≤ 64 Kio, très loin d'un débordement ; notre défaut est un **sous-dimensionnement d'allocation** | **NE S'APPLIQUE PAS** (nature différente) |
| FastFlowLM **#636 / #743** (plugins d'opérateurs ; prefill 670 ms vs 929 ms) | mesurer un gain **sur un modèle**, pas sur un GEMM isolé | nous n'avons mesuré que des noyaux isolés | **EXTERNE**, non transféré — fixe la priorité §11 P2 |

---

## 9. État Git exact

| Élément | Valeur |
|---|---|
| Racine | `C:/Users/videl/skills-audit-reports` |
| HEAD | `b8dba31` (inchangé) |
| Divergence | `git rev-list --left-right --count origin/main...HEAD` → `0 2` (2 commits locaux **antérieurs** à cette session : 08:44 et 08:57) |
| Modifié non indexé | `INDEX.md` |
| Non suivis | `AGENTS.md`, `audits/xdna2-overhead-20261018/`, `audits/skills-fix-20261018/`, `audits/skills-usage/`, `tests/`, `tools/*.py` (4) |
| **Commit / push de cette session** | **AUCUN** |

---

## 10. Limites assumées

- La borne de B sur le design 512 est encadrée en (7 995 392 ; 8 388 608] : pas bisectée finement.
- `arg0`/`arg2` du design 512 : non bisectés vers le bas.
- **word[6] des BD : layout UNKNOWN** → aucune formule d'étendue close n'existe encore ; le
  pré-vol reste un garde-fou empirique + planchers mesurés, jamais une preuve.
- Le pré-vol ne détecte que le sous-dimensionnement : il ne dit rien de la justesse.
- Seuls 2 designs sur 37 dépôts disposent de planchers mesurés.
- Les issues publiques citées (§8) sont des **pistes**, non des preuves locales ; aucune
  n'a été vérifiée sur cette machine.
- Le clone `repos_mlir_aie` est superficiel (1 commit) : pas de datation des changements de format.

---

## 11. Prochaine action choisie automatiquement

| Pri | Action | Pourquoi elle est prioritaire | Coût |
|---|---|---|---|
| **P1** | Décoder word[6] depuis `AIEDmaToNpu.cpp` (émission `NpuWriteBdOp` + encodeurs ND) et remplacer la formule empirique par les champs réels (d0/d1/d2 sizes & strides + `iteration_size`) | Supprime la classe entière de faux PASS démontrée §6 | statique, hors matériel |
| **P1** | Bisecter B du design 512 dans (7 995 392 ; 8 388 608] à 8 répétitions, référence numérique | Fixe le plancher exact là où la règle échoue de 37 % | ~10 runs |
| **P2** | Mesurer un gain **sur un modèle** (OpenFlowLM-Next / FLM), pas sur un noyau isolé | Seul moyen de savoir si 5,7 % du pic se traduit en tokens/s | long |
| **P2** | Chercher `0x00CD0CD0` et les motifs MemTile dans les sorties archivées (#3840) | Élimine ou confirme une 3ᵉ cause de données fausses | lecture seule |
| **P3** | Instrumenter le noyau (compteurs AIE, trace de cycles) pour expliquer les ×17,6 | Le recouvrement est écarté (+10,8 %) : le limiteur est dans le design | moyen |
