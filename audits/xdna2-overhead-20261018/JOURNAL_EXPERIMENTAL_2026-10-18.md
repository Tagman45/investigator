# Journal expérimental — NPU XDNA2 sous Windows — 18/10/2026 (session 2)

**Objet** : exécuter réellement les tests A–E de la mission (référence sans patch, visibilité
mémoire, patches BD, sorties, SIGSEGV), puis inspecter l'ABI de `mm.xclbin`.
**Aucun commit, aucun push.** Les rapports et preuves du matin sont **conservés** (aucun fichier
antérieur modifié, sauf ajout d'une section de corrections datée dans le rapport maître).

| Élément | Valeur mesurée |
|---|---|
| Hôte | Nitro AN16S-61, Ryzen AI 9 365 |
| XRT | 2.21.0 (HEAD) |
| Pilote NPU | 32.0.20101.3760 |
| Firmware NPU | 1.1.2.64 |
| pyxrt | `C:\Users\videl\miniconda3\Lib\site-packages\pyxrt.pyd` |
| Python | 3.13.13 |
| xclbin testé | `E:/trixdna_test/phase5_atb/phase5_atb_m32k64n128.xclbin` |
| insts testé | `E:/trixdna_test/phase5_atb/phase5_atb_m32k64n128_insts.bin` (5168 o, 1292 mots) |

Toutes les commandes ont été lancées depuis
`C:/Users/videl/skills-audit-reports/audits/xdna2-overhead-20261018` avec `python -u` (sortie non
tamponnée : un SIGSEGV ne doit pas masquer les mesures déjà imprimées).

---

## T0 — Structure du TXN (préalable, exécuté)

```
python -u scripts/txn_dump.py --insts <insts> --json evidence/txn_struct.json
```

* exit **0** ; walk **COHERENT** : 136 records = `numops` 136.
* header : `Major=0 Minor=1 DevGen=4 rows=6 cols=8 memtile_rows=1 txnsize=5168`.
* ops : `BLOCKWRITE=40  DDR_PATCH=40  WRITE=40  MASKWRITE=8  TCT=8`.
* **Aucune** opération `LOADPDI`, **aucun** registre de tuile compute (`0x2xxxx`, `0x3xxxx`) :
  toutes les adresses de registre sont dans `0x1D000–0x1D2FF` (shim DMA), cols 0–3, row 0.
* Contrat implicite (tailles déduites des BD, **pas** d'un manifeste) :
  `arg0` offsets ≤ `0x1e0000` + len 32768 ; `arg1` ≤ `0xc0000` + 65536 ; `arg2` ≤ `0x80300` + 16384.
* Preuves : `evidence/txn_struct.json` `1ba5e61f…`, `evidence/txn_struct.txt` `b3cabe1e…`.

---

## Test A — référence sans patch / sensibilité aux entrées

**A1 (matin, invalide a posteriori)** : `python -u scripts/npu_exp.py sensitivity`
→ `A1_B1` et `A1_B1_bis` **diffèrent de 170 276 octets** : non déterministe, donc
« C dépend de A » **n'était pas démontrable**. Verdict : **INCONCLUSIVE**, cause identifiée en D.

**A2 (après correction des tailles)** :

```
python -u scripts/npu_exp.py sensitivity --asize 4194304 --bsize 2097152 --csize 2097152 \
    --json evidence/exp_A_sensitivity_bigBO.json
```

| run | état | sha256(C) |
|---|---|---|
| `A1_B1` | `ERT_CMD_STATE_COMPLETED` | `7330e0d510ac5724…` |
| `A1_B1_bis` | idem | `7330e0d510ac5724…` (**identique**) |
| `A2_B1` (A modifié) | idem | `d380b10e06961cdc…` |

* **PASS déterministe** : deux exécutions, mêmes entrées → C **bit-identique**.
* **PASS sensibilité** : changer uniquement A change C sur **500 032 / 1 048 576 octets**.
* exit **0**. Preuves : `exp_A_sensitivity_bigBO.json` `f15af4c0…`, `.txt` `09ebefc0…`.
* `exp_A_sensitivity.json` `b6ba426b…` = trace du test **invalide** conservée pour mémoire.

---

## Test B — visibilité mémoire

### B1 — aller-retour hôte → device → hôte, **sans soumission**

```
python -u scripts/npu_exp.py visibility --json evidence/exp_B_visibility.json
```

| taille BO | flags | aller-retour identique | 2e aller-retour |
|---|---|---|---|
| 16 384 | `cacheable` | oui | oui |
| 16 384 | `host_only` | oui | oui |
| 544 768 | `cacheable` | oui | oui |
| 544 768 | `host_only` | oui | oui |

**PASS_VISIBILITE** (4/4). exit **0**. `exp_B_visibility.json` `c4aa4683…`.
→ la cohérence mémoire **n'est pas** le défaut, à ces tailles et sur les deux types de BO.

### B2 — sémantique exacte de `bo.read()`

```
python -u scripts/npu_readsem.py
```

| étape | observation |
|---|---|
| t0 aller-retour du marqueur M1 | identique |
| t1 après `wait()` + `sync FROM` | contenu **neuf** (`0x8e8000…`) : le NPU a bien écrit |
| t2 `write(M2)` **sans** sync + `read` | renvoie M2 (mapping hôte visible) |
| t3 `sync FROM` après `write` | renvoie **encore** M2 |
| t4 `sync TO` + `sync FROM` | M2 (aller-retour réel) |

Lecture : le mapping est cohérent ; la donnée lue en t1 est bien celle écrite par le NPU, et non un
cache hôte périmé (sinon t1 aurait rendu M1). Preuve : `exp_B2_read_semantics.json` `161b87ba…`.
**Limite** : on ne peut pas distinguer « sync réel » de « mapping cohérent » ; sans effet ici.

---

## Test C — sémantique des patches BD

### C1 — contrôle négatif : opcode 1 (PMC) ne doit rien transférer

```
python -u scripts/npu_exp.py map --opcode 1 --json evidence/exp_neg_opcode1_map.json
```

`ERT_CMD_STATE_COMPLETED` et **0 mot modifié sur les trois BO**. Donc : `COMPLETED` seul ne prouve
rien, et **les écritures observées avec opcode 3 viennent bien du TXN**.
Preuve : `exp_neg_opcode1_map.json` `28140a34…`.

### C2 — `arg_plus := 0` sur les 40 patches (seule variable modifiée)

```
python -u scripts/npu_exp.py patch0 --json evidence/exp_C_patch0.json
```

Résultat : **32 768 mots modifiés en 512 plages de 64 mots**, départs `0, 256, 512, 768, 1024, …`
(soit un pas de **1 024 octets**, 256 octets écrits par pas).

### C3 — `arg_plus := 0x1000` sur les 40 patches (même méthode)

```
python -u scripts/npu_exp.py patchsent --json evidence/exp_C_patchsent.json
```

Même forme, **décalée de exactement +1 024 mots = +4 096 octets = +`0x1000`** (départs
`1024, 1280, 1536, …`).

**Conclusion C2+C3 : PASS — `arg_plus` est appliqué et linéaire, au byte.** Une variation de
`0x1000` décale toute l'empreinte de `0x1000`. L'hypothèse « les patches sont ignorés » est
**réfutée**. Preuves : `exp_C_patch0.json` `413ae5d0…`, `exp_C_patchsent.json` `60b8d78f…`.

### C4 — repli de l'ouverture DDR AIE (`arg_plus += 0x80000000`)

```
python -u scripts/npu_exp.py patchfold --json evidence/exp_C_patchfold_run1.json
```

`ERT_CMD_STATE_COMPLETED` mais **0 octet écrit** dans C. Le chemin XRT Windows + pilote actuel
**n'attend pas** l'adresse dans l'ouverture `0x80000000` pour ces buffers ; forcer
`kDDRAIEAddrOffset` dans `arg_plus` **supprime tout transfert**.
→ L'hypothèse « il manque le fold `0x80000000` » est **réfutée** pour cette pile.
Preuve : `exp_C_patchfold_run1.json` `4458418c…`.

---

## Test D — sorties : cause de l'échec établie

### D1 — carte de base (tailles du matin : A 1 998 848 / B 851 968 / C 544 768)

```
python -u scripts/npu_exp.py map --json evidence/exp_D_map_baseline.json
```

* `pre_roundtrip_identique = {bo0: true, bo1: true, bo2: true}` (marqueur en place avant soumission)
* état `COMPLETED` ; **bo2 : 136 192 / 136 192 mots modifiés** = **tout le buffer**, pas les
  8 tuiles attendues ; bo0/bo1 intacts.
* `exp_D_map_baseline.json` `2a9e6738…`

### D2 — contenu réel de C (1re caractérisation)

```
python -u scripts/npu_dump_c.py --json evidence/exp_D_content_run1.json --save-bin evidence/exp_D_C_run1.bin
```

* 9 941 valeurs distinctes, 44 896 zéros ; mots `0x8e8000`, `0x8e9800`, `0x8eb000`… (pas `0x1800`)
  avec redémarrage tous les 128 mots ; **aucune** occurrence de `0xDEAD` (A) ni `0xBEEF` (B).
* `exp_D_content_run1.json` `05fa2e37…`, binaire `exp_D_C_run1.bin` `4b1fa5d0…`

### D3 — l'empreinte dépend-elle de la taille du BO ?

```
python -u scripts/npu_exp.py map --csize 2097152 --json evidence/exp_D_map_c2M.json
```

C = 2 Mo → **262 144 mots modifiés = exactement 1 MiB**, contigus `[0, 262143]`.
→ l'empreinte **suit la taille du buffer jusqu'à 1 MiB** : les écritures dépassent largement
544 768 octets. Preuve : `exp_D_map_c2M.json` `f47e9f2b…`.

### D4 — tailles correctes : reproductibilité

```
python -u scripts/npu_exp.py map --asize 4194304 --bsize 2097152 --csize 2097152 \
    --json evidence/exp_D_bigBO_runN.json      (N = 1, 2)
```

| run | état | écrit dans C | sha256(C) |
|---|---|---|---|
| 1 | `COMPLETED` | 262 144 mots, **dans les limites** | `cf078a1d31559700…` |
| 2 | `COMPLETED` | idem | `cf078a1d31559700…` **identique** |

→ **PASS reproductibilité.** A et B intacts. Preuves : `exp_D_bigBO_run1.json` `9a055950…`,
`run2` `d45870b3…`.

### D5 — isolation : quel buffer était sous-dimensionné ?

Deux exécutions par configuration, C = 2 Mo :

| A | B | déterministe |
|---|---|---|
| 4 194 304 | 851 968 (nominal) | **non** (`exp_D_iso_4194304_851968_*` `bbf43659…` / `3b81b585…`) |
| 1 998 848 (nominal) | 2 097 152 | **oui** (`exp_D_iso_1998848_2097152_*` `c4dd9045…` / `027b7b00…`) |
| 1 998 848 | 2 097 152 | oui (D4) |
| 1 998 848 | 1 048 576 | **non** (`exp_D_bracket_B1048576_*` `b5551bf0…` / `fc26fee2…`) |
| 1 998 848 | 917 504 | **non** (`exp_D_bracket_B917504_*` `ebaae6dd…` / `994975d7…`) |
| 1 998 848 | 851 968 (nominal), C seul agrandi | **non** (`exp_D_onlyC_*` `742ad556…` / `4922964a…`) |
| 1 998 848 | 1 048 576, **exit capturé** | **non**, exit **0** / **0** (`exp_D_bracket_B1048576_rc1.json` `c0f9f45c…`, `rc2` `c81a242a…`) |

**Traçabilité des codes de sortie** : chaque exécution listée ci-dessus a produit un JSON relu ;
les exits ont été **explicitement capturés** pour `ctx*` (E), `map` nominal (`0`), `patch0` (`0`),
`patchsent` (`0`), `patchfold` (`0`), `bigBO` (`0` ×2), `B1048576_rc` (`0` ×2) et `ctrlcode` (`0` ×2).
Les exécutions `exp_D_iso_*`, `exp_D_bracket_B917504_*` et `exp_D_onlyC_*` ont été lancées dans une
boucle redirigée **sans capture du code de sortie** : leur statut est établi par l'artefact JSON
produit et relu, **pas** par un exit vérifié — limitation consignée, non compensée.

**Cause établie (D)** : le buffer **B** était sous-dimensionné. À `B = 851 968` (valeur « exacte »
déduite des `arg_plus`) le NPU lit **au-delà** de l'allocation ; la mémoire lue varie d'une
exécution à l'autre, ce qui rend C **non déterministe**. Agrandir B (2 Mio) rend le résultat
**reproductible bit à bit**. A (1 998 848) est suffisant ; C doit être ≥ 1 MiB.

**Mécanisme ABI expliqué** : les BD ne sont **pas** des transferts plats. Le mot BD `0x04000000`
porte la composante de stride `0x400` (1 024 o) ; `gemm.dll` documente les champs
`D0 size/stride`, `D1 size/stride`, `D2 stride` + `Inferred D2 size`, ce qui décrit un transfert
**3D** dont l'empreinte est bien supérieure à `buffer_length`. Dimensionner sur
`max(arg_plus) + buffer_length` (méthode du matin) **sous-estime** donc systématiquement.

### D6 — justesse numérique

**NOT TESTED / UNKNOWN** : le contrat de forme (M, K, N, layout, strides) du design n'est écrit ni
dans le xclbin, ni dans le TXN, ni dans un manifeste. Aucun PASS numérique n'est possible sans lui.

---

## Test E — SIGSEGV au teardown (matrice, un process par cas)

```
python -u scripts/npu_exp.py teardown --case <cas> --json evidence/exp_E_<cas>.json
```

| cas | BO vivants à la sortie | exit |
|---|---|---|
| `ctx` (device+xclbin+hw_context+kernel, sans BO) | 0 | **0** |
| `ctx_bo16k` | 1 × 16 Kio | **139** |
| `ctx_bo16k_del` (destruction explicite) | 0 | **0** |
| `ctx_bo544k` | 1 × 544 Kio | **139** |
| `ctx_bo544k_del` | 0 | **0** |
| `ctx_bo3` | 3 (1,9 Mo + 0,85 Mo + 0,54 Mo) | **139** |
| `ctx_bo3_del` | 0 | **0** |
| `bo_group0` (allocation avec `group_id=0` en dur) | — | **139** (immédiat) |

**Cause établie (E)** : le SIGSEGV est un **problème d'ordre de destruction** : tout `bo` encore
vivant à l'arrêt de l'interpréteur provoque une violation d'accès. La **taille n'est pas le
facteur** (16 Kio plante comme 544 Kio) ; détruire les BO avant la sortie **supprime** le crash.
Un second défaut est isolé : `pyxrt.bo(dev, taille, flags, 0)` (groupe de banque 0) **plante
immédiatement** ; il faut `kernel.group_id(n)`.

---

## Test F — alternative réelle : un ctrlcode NPU2 déjà présent sur disque

Des dumps de ctrlcode existent localement — l'affirmation « aucun flux sur disque » doit donc être
précisée. Test de l'alternative la plus proche : `tools_ctrlcodes/generated_phase5_ctrl.bin`
(8 400 o, `devgen=4`, `cols=8`, walk **COHERENT**, 224 ops, **64 BD**, patchs arg0/1/2 =
2 Mio / 4 Mio / ~0,5 Mio).

```
python -u scripts/npu_exp.py map --insts /e/trixdna_test/tools_ctrlcodes/generated_phase5_ctrl.bin \
    --asize 8388608 --bsize 8388608 --csize 2097152 --json evidence/exp_F_ctrlcode_runN.json
```

| run | exit | état | mots modifiés |
|---|---|---|---|
| 1 | **0** | `ERT_CMD_STATE_TIMEOUT` | 0 / 0 / 0 |
| 2 | **0** | `ERT_CMD_STATE_TIMEOUT` | 0 / 0 / 0 |

→ **FAIL (non interchangeable)** : ce ctrlcode, pourtant NPU2 et cohérent, **ne s'exécute pas** sur
`phase5_atb_m32k64n128.xclbin` (timeout, aucun octet). Cela **confirme** que le ctrlcode est lié à la
topologie du xclbin (claim #24) et que `_insts.bin` (qui rend `COMPLETED`) est le bon appariement
pour **ce** xclbin. Preuves : `exp_F_ctrlcode_run1.json` `82022e25…`, `run2` `743e400d…`.

**[COMPLÉTÉ 18/10/2026, série 2]** Ce même fichier est **octet pour octet identique** à
`repos_strixhalo_npu_setup/saved_xclbins/phase5_bf16_512x8192x512_insts.bin`
(sha256 `487fa1ff…` des deux côtés). Test F avait donc utilisé **le bon ctrlcode avec le mauvais
xclbin** ; l'appariement correct, exécuté en Test H, donne **PASS_NUMERIQUE** (§H). La conclusion
« non interchangeable » n'est pas affaiblie : c'est précisément l'appariement qui compte.

Autres dumps examinés (hors appariement, donc non soumis) :

| fichier | header | walk | raison de non-soumission |
|---|---|---|---|
| `full_txn.bin`, `qwen36_npu/full_txn.bin`, `OUT_F876/full_txn.bin` | `devgen=1`, `cols=4`, `txnsize` = moitié de la taille fichier | INCOHERENT (233/232) | génération/format différents (AIE1), pas NPU2 |
| `generated_sequence.bin` | `devgen=1`, `cols=4`, 15 ops, 1 BD de 4 Mio | COHERENT | préambule de config, pas un run de design |
| `flm_gemm_sequence.bin` | `devgen=4`, 9 ops, 2 BD de 1 Kio | COHERENT | 2 BD seulement : préambule, pas un GEMM |

## §4 — ABI et contrat de `mm.xclbin`

```
xclbinutil --dump-section EMBEDDED_METADATA:RAW:evidence/mm_metadata.xml \
           --input "C:/Program Files/flm/xclbins/DeepSeek-R1-0528-Qwen3-8B-NPU2/mm.xclbin"
```

* exit **0** ; noyau `MLIR_AIE`, `dpu_kernel_id=0x901`, **8 arguments** :
  `opcode(u64)`, `instr(char*)`, `ninstr(u32)`, `bo0…bo4(void*)` — **même ABI** que `phase5`.
* **Aucun flux d'instructions pour `mm.xclbin`** : `find "C:/Program Files/flm" -maxdepth 3
  -name '*.bin' -o -name '*.elf' -o -name '*.insts'` → **0 résultat**. Les dumps présents ailleurs
  (`E:/trixdna_test/...`) appartiennent à d'autres designs (`devgen=1`/`cols=4` pour la famille
  `full_txn.bin`) et le candidat NPU2 le plus proche a été **testé et rejeté** (Test F : timeout).
* Le flux est **généré au runtime** : `gemm.dll` (165 376 o) contient l'assembleur/désassembleur
  TXN (`Write 32`, `DDR patch`, `DMA block write`, `Issue token`, `Wait sync`,
  `--Buffer length`, `--D0 size, stride`, `--D1 size, stride`, `--D2 stride`,
  `--Inferred D2 size`, `--Argument index`, `--Argument offset (Bytes)`) et les contrôles
  d'alignement `GEMM M size not aligned with total npu rows`, `GEMM K size not aligned with k`,
  `GEMM N size not aligned with n`.
* **Verdict : NOT TESTED** — exécuter `mm.xclbin` exige de **capturer** ce flux (hook API) ou de le
  reconstruire ; c'est le **premier prérequis manquant**. Aucun PASS numérique n'est revendiqué.
* Preuve : `evidence/mm_metadata.xml` `67bdb7a4…`.

---

## Récapitulatif des statuts

| # | Affirmation | Statut | Preuve |
|---|---|---|---|
| 1 | Cohérence mémoire hôte↔device correcte (deux flags, deux tailles) | **PASS** | `exp_B_visibility.json` |
| 2 | Données lues après `wait()` = données écrites par le NPU (pas un cache) | **PASS** | `exp_B2_read_semantics.json` |
| 3 | `COMPLETED` ne prouve pas l'exécution (opcode 1 : 0 transfert) | **PASS** | `exp_neg_opcode1_map.json` |
| 4 | `arg_plus` appliqué et linéaire au byte (+`0x1000` → +`0x1000`) | **PASS** | `exp_C_patch0/patchsent` |
| 5 | Patches ignorés par le firmware | **REFUTED** | idem |
| 6 | Fold `0x80000000` nécessaire | **REFUTED** (supprime tout transfert) | `exp_C_patchfold_run1.json` |
| 7 | Empreinte C = 8 tuiles de 16 Kio | **REFUTED** (1 MiB, strided) | `exp_D_map_c2M.json` |
| 8 | Cause du `FAIL_STRUCTUREL` = buffers sous-dimensionnés (B en particulier) | **PASS** | `exp_D_iso_*`, `exp_D_bracket_*` |
| 9 | Résultat reproductible avec tailles correctes | **PASS** | `exp_D_bigBO_run1/2` |
| 10 | C dépend de A | **PASS** | `exp_A_sensitivity_bigBO.json` |
| 11 | SIGSEGV = ordre de destruction des BO (taille non pertinente) | **PASS** | `exp_E_*` |
| 12 | `pyxrt.bo(..., group_id=0)` plante | **PASS** | `exp_E_bo_group0` (exit 139) |
| 13 | Justesse numérique du GEMM | **UNKNOWN / NOT TESTED** | contrat de forme absent |
| 14 | Exécution de `mm.xclbin` | **NOT TESTED** (flux absent) | §4 |

## Prochaine expérience (une variable à la fois)

1. **Test de linéarité, indépendant de la forme** : A rempli de BF16 propres (`1.0`, `0.5`),
   puis `2·A` ; si `C(2A) = 2·C(A)` composante par composante, le chemin est une application
   linéaire compatible GEMM ; sinon, le contrat A→C est établi comme non-GEMM. (Tailles D4.)
2. **Contrat de forme** : extraire M/K/N réels depuis `gemm.dll` (constantes d'alignement) ou par
   capture du flux TXN de FLM, avant toute référence numérique.
3. **`mm.xclbin`** : hook API sur `gemm.dll` / `dyn_dispatch_core.dll` pour capturer le TXN et les
   adresses d'arguments, puis rejouer via `pyxrt` avec les tailles **calculées depuis les
   descripteurs 3D** (jamais depuis `arg_plus + buffer_length`).

---

# Série 2 — bornage, descripteurs, validation numérique (même journée)

Ordre suivi : (1) bornage de B, (2) bornes des descripteurs 3D, (3) validation numérique,
(4) cycle de vie des ressources, (5) recherche du flux de `mm.xclbin`.

## G — Bornage de B (point 1)

```
python -u scripts/bracket_B.py      # 5 tailles × 3 répétitions, chaque run en sous-processus
```

| B (octets) | Mio | exits | hash distincts | déterministe | état ERT |
|---|---|---|---|---|---|
| 1 048 576 | 1,0000 | 0,0,0 | 3 | **non** | COMPLETED |
| 1 048 592 | 1,0000 | 0,0,0 | 3 | **non** | COMPLETED |
| 1 101 056 | 1,0500 | 0,0,0 | 3 | **non** | COMPLETED |
| 1 310 720 | 1,2500 | 0,0,0 | 3 | **non** | COMPLETED |
| 1 572 864 | 1,5000 | 0,0,0 | 3 | **non** | COMPLETED |
| 1 835 008 | 1,7500 | 0,0,0 | 3 | **non** | COMPLETED |
| **2 097 152** | **2,0000** | 0,0,0 | **1** | **oui** | COMPLETED |

Seuil : **B > 1,75 Mio**, plus petite taille reproductible mesurée = **2 097 152 octets** —
c'est **exactement** l'étendue prédite par les descripteurs (§I). Marge nulle : à 1,75 Mio
(1 835 008) il manque 262 144 octets, et le résultat reste non reproductible.
`COMPLETED` dans les 7 cas / 21 runs : l'état ERT ne discrimine rien (confirmé).
Preuves : `exp_G_bracket_B.json` `3dc2f824…` (1,00–1,25 et 2,00),
`exp_G_bracket_B_mid.json` `b5a04168…` (1,50 et 1,75), + 21 JSON individuels.

## I — Bornes des descripteurs 3D (point 2)

```
python -u scripts/descriptor_bounds.py --json evidence/exp_I_descriptor_bounds.json
```

Modèle de champ (validé, **pas** supposé) :
`étendue(BD) = arg_plus + (payload[6] >> 16) × 0x10000 + buffer_length`

| arg | BD | plus_max | itérations | len | **étendue requise** | taille mesurée suffisante | verdict |
|---|---|---|---|---|---|---|---|
| 0 (A) | 16 | `0x1e0000` | 0 | 32 768 | **1 998 848** | 1 998 848 | **PASS** (égalité exacte) |
| 1 (B) | 16 | `0xc0000` | 19 | 65 536 | **2 097 152** | 2 097 152 | **PASS** (égalité exacte ; 1,25 Mio échoue) |
| 2 (C) | 8 | `0x80300` | 16 | 16 384 | **1 590 016** | 2 097 152 | **PASS** (544 768 < requis ⇒ cohérent) |

Le modèle **prédit exactement** la borne mesurée en G (2 097 152) et la valeur exacte d'A.
La correction n'est donc **pas** déduite du fait que le kernel termine : elle est calculée depuis
les descripteurs, puis confrontée à une mesure indépendante.
Preuve : `exp_I_descriptor_bounds.json` `d042408b…`.

## H — Validation numérique contre référence (point 3)

Référence verrouillée dans `E:/trixdna_test/docs/EVID_D_PHASE5_GEOMETRY_2026-08-10.md` :
`phase5_bf16_512x8192x512` — **M=512, K=8192, N=512** ; A et B = BF16 `0x3F80` (1.0) ;
C = F32, M×N = 262 144 valeurs ; attendu **C = K = 8192.0** ; BO de **16 Mio** dans le harnais validé.

```
python -u scripts/npu_gemm_ref.py --reps 2 --json evidence/exp_H_gemm_ref.json
```

| run | état | correctes | fausses | nan | min / max | C[0:4] | temps |
|---|---|---|---|---|---|---|---|
| 1 | COMPLETED | **262 144 / 262 144** | 0 | 0 | 8192.0 / 8192.0 | 8192.0 ×4 | 4,742 ms |
| 2 | COMPLETED | **262 144 / 262 144** | 0 | 0 | 8192.0 / 8192.0 | 8192.0 ×4 | 1,880 ms |

sha256(C) identiques entre les deux runs ⇒ **PASS_NUMERIQUE**, exit **0**.
Référence CPU indépendante : `C[i][j] = Σ_k 1·1 = K` (aucun code du design réutilisé).
Preuve : `exp_H_gemm_ref.json` `419ebbab…`.
**Ce PASS porte sur `phase5_bf16_512x8192x512`, pas sur `phase5_atb_m32k64n128`.**

## Cycle de vie (point 4)

* `npu_gemm_ref.py` détruit explicitement `boA/boB/boC/bi` avant sortie : **2 runs, exit 0**.
* `bracket_B.py` : **21 sous-processus, 21 exit 0** (7 tailles × 3), aucune trace de SIGSEGV.
* Rappel de la matrice E : tout BO vivant à l'arrêt de l'interpréteur ⇒ exit 139 ; destruction
  explicite ⇒ exit 0, quelle que soit la taille.
⇒ le correctif de cycle de vie est **appliqué et répété sans réapparition du crash**.

## Recherche du flux de `mm.xclbin` (point 5)

Balayage ciblé (pas de récursion sur E:) :

| artefact | constat |
|---|---|
| `Program Files/flm/xclbins/.../mm.xclbin` | sha256 `4afc2a6f…`, 512 220 o, ABI `MLIR_AIE`, 8 args |
| `E:/trixdna_test/mm_metadata.xml`, `mm_embedded_meta_dump.xml` | **identiques octet pour octet** à la metadata du `mm.xclbin` de FLM (`67bdb7a4…`) |
| `E:/trixdna_test/aiebu_extract/mm/…pdi` | **PDI du mm.xclbin déjà extrait** (500 960 o) + `AIE_PARTITION.json` |
| `E:/trixdna_test/disasm/mm.asm` | 89 002 o — désassemblage du programme de cœurs, pas un TXN |
| `E:/trixdna_test/mm_custom.xclbin` | sha256 `c09be728…` ⇒ **différent** du mm.xclbin de FLM |
| `E:/trixdna_test/mm_custom.seq` | TXN cohérent mais **`cols=1`**, 11 ops, 3 BD de 2 048 o ⇒ autre topologie |
| `E:/trixdna_test/hook_ctrlcode_dump.dll` | outil de capture de ctrlcode présent localement |

**Verdict point 5** : la metadata et le **PDI** de `mm.xclbin` sont déjà extraits, mais son **TXN
n'existe pas sur disque** ; le seul `.seq` disponible appartient à une variante 1 colonne.
`NOT TESTED` pour l'exécution, avec prérequis nommé : **capturer le TXN** (`hook_ctrlcode_dump.dll`)
ou le régénérer (`tools_ctrlcodes/gen_ctrlcode_aie2p.py`) pour la topologie exacte de `mm.xclbin`.

## Statuts de la série 2

| Affirmation | Statut | Preuve |
|---|---|---|
| B reproductible à partir de 2 097 152 o, pas à 1 835 008 (7 tailles × 3 répétitions) | **PASS** | `exp_G_bracket_B.json`, `exp_G_bracket_B_mid.json` |
| `COMPLETED` ne discrimine pas la correction | **CONFIRMÉ** (5 tailles, même état) | idem |
| Étendue requise calculable depuis les descripteurs 3D et égale à la mesure | **PASS** | `exp_I_descriptor_bounds.json` |
| GEMM `phase5_bf16_512x8192x512` numériquement correct et reproductible | **PASS_NUMERIQUE** | `exp_H_gemm_ref.json` |
| Crash de teardown absent après destruction explicite, sur 23 runs | **PASS** | `exp_G`, `exp_H`, `exp_E` |
| TXN de `mm.xclbin` présent sur disque | **REFUTED** | sha/diff ci-dessus |
| Exécution de `mm.xclbin` | **NOT TESTED** (prérequis : TXN) | — |
