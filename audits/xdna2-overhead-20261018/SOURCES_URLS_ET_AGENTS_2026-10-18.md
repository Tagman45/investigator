# Sources externes vérifiées + agents REA — 18/10/2026

Audit : `audits/xdna2-overhead-20261018` — mission : identifier et éliminer les surcoûts et
défauts du runtime NPU XDNA2 sous Windows (Ryzen AI 9 365 · pilote 32.0.20101.3760 · FW 1.1.2.64 · XRT 2.21.0).

Règle appliquée (`evidence`) : **aucune affirmation sans statut + preuve localisable.**
Règle appliquée (`xdna2-cross-audit`) : toute source externe est liée à une affirmation locale
et à une expérience discriminante — pas seulement citée.

Statuts utilisés : `VÉRIFIÉ-CONTENU` (page lue dans cette session, passage cité) ·
`VÉRIFIÉ-HTTP` (200 + sha256, corps non lu) · `NON TESTÉ` · `RÉFUTÉ` · `CONFIRMÉ` · `INCONCLUSIF`.

**Aucun commit, aucun push. Aucun fichier de preuve antérieur écrasé.**

---

## 1. URLs — état de vérification

### 1.1 VÉRIFIÉ-CONTENU (page récupérée et lue dans cette session)

| # | URL | HTTP | Ce que la source dit (passage) | Affirmation locale concernée |
|---|---|---|---:|---|
| 1 | https://github.com/Xilinx/mlir-aie/issues/3653 | 200 | « XRTTensor creates host BOs with `group_id=0`… Running with group-0 BOs against kernels that declare non-zero groups yields **silently wrong results (ERT reports `ERT_CMD_STATE_COMPLETED`, the NPU never touches the data buffers)** » | Un `COMPLETED` ne prouve pas la justesse → notre borne B est un défaut de **classe voisine**, pas la même cause (`group_id=0` écarté : nos harnais passent `kern.group_id(3+i)`) |
| 2 | https://github.com/amd/xdna-driver/issues/1645 | 200 | Réponse AMD (maxzhen) : « **the driver does not validate the command before sending it out** » ; stsoe : « There is no kernels.json input to XRT… I was not aware of anything but default 0 group for kernels on AIE2 » | Aucune validation côté pilote : le garde-fou doit être **hôte**, pas attendu du driver |
| 3 | https://github.com/Xilinx/mlir-aie/issues/3033 | 200 | « `Buffer_Length` for buffer descriptors is a **32-bit register**, with meaning *buffer length (number of 32-bit words)*… conversion… via an intermediate step to number of bytes, which can then overflow » (fermé par #3034) | **Unité** : la longueur matérielle est en mots de 32 bits, pas en octets → toute borne décodée doit être `mots × 4` ; et un chemin d'encodage peut déborder |
| 4 | https://github.com/Xilinx/mlir-aie/issues/3910 | 200 | Full-ELF Windows : séquence correcte `xrt::elf` → `xrt::hw_context(device, elf)` → `xrt::ext::kernel(ctx,"main:sequence")` ; piège `run.set_arg()` → cast `static_cast<xrt::bo&>` ; « 100/100 completed » mais « **numerical correctness still pending** » | Chemin Full-ELF **répétable** sous Windows mais **non validé numériquement** → ne pas l'utiliser comme preuve de correction |
| 5 | https://github.com/Xilinx/mlir-aie/issues/3840 | 200 | « npu2: column-0 MemTile word 0 reads back as `0x00CD0CD0` after the first dispatch… Only a buffer loaded once, at PDI load, keeps the bad value » (workaround dans `AIEAssignBuffers.cpp`) | État persistant entre dispatches : piste pour expliquer un hash identique après réutilisation (exp_P order2), **non démontrée chez nous** |
| 6 | https://github.com/Xilinx/mlir-aie/issues/3908 | 200 | Wheel MLIR : `MLIR_ENABLE_THREADS` non défini → tout contexte mono-thread ; `aiecc` 5,72 s → **4,26 s**, `aie-opt` 2,18 s → **0,99 s**, sorties **identiques octet par octet** | Optimisation du **temps de compilation** seulement — pertinente si les agents recompilent des candidats IRON/MLIR-AIE |
| 7 | https://github.com/Xilinx/mlir-aie/discussions/3390 | 200 | Discussion de conception compilateur ↔ format binaire ↔ dispatch ↔ topologie mémoire | Sert à cadrer les contrôles de conformité ; **n'est pas** une mesure locale (VÉRIFIÉ-HTTP pour le détail, corps tronqué) |
| 8 | https://github.com/ROCm/FastFlowLM/issues/636 | 200 | Issue ouverte par l'auteur de cet audit (gatman45) : mesures propres étiquetées `[MY MEASUREMENT]`, instrumentation XRT par wrapper Detours + ETW, renvoi à arXiv:2512.13282 | **C'est notre propre rapport public** → auto-cohérence, jamais une validation indépendante |
| 9 | https://github.com/ROCm/FastFlowLM/pull/743 | 200 | « plugin mechanism for operator overrides » : `flm_plugin.hpp`, `FLM_PLUGIN`, `hook_result::defer()` ; exemple `src/plugins/iron_gemm` ; prefill Gemma4-E2B 247 tokens : 672 ms vs 714 ms ; 702 ms vs 959 ms | Voie **crédible** pour tester une fusion d'opérateurs sans remplacer FLM — état de merge **non affiché** sur la page lue (`INCONCLUSIF` sur le statut) |
| 10 | https://docs.amd.com/r/en-US/ug1079-ai-engine-kernel-coding/Tiling-Parameters-and-Buffer-Descriptors | 200 | UG1079 : `traversing_parameters` = `{dimension, stride, wrap}`, **wrap = nombre d'éléments à parcourir** | Sens sémantique des champs `d0/d1/d2` — cohérent avec le décodage source (§2) |
| 11 | https://docs.amd.com/r/en-US/Vitis-Tutorials-AI-Engine-Development/Debugging-Memory-Access-Violations | 200 | « `--enable-memory-check` detects these out of range memory accesses » — option **d'émulation** ; « negatively impacts runtime performance » | La détection hors-bornes n'existe **que dans l'émulateur** : aucun témoin matériel → le garde-fou hôte est la seule barrière |
| 12 | https://arxiv.org/abs/2512.13282 | 200 | « up to 6.76 TOPS (XDNA) and **38.05 TOPS (XDNA2)** int8 ; **14.71 TOPS** (XDNA2) bf16 » (Taka et al., 15/12/2025) | Référence de marge pour notre 3,35 TFLOP/s bf16 — **benchmark optimisé**, pas un débit garanti |

### 1.2 VÉRIFIÉ-HTTP seulement (200 + sha256 + taille, corps non lu)

Corps non exploitable dans cette session (tronqué à 200 001 o) — **à ne pas citer comme preuve de contenu**.

| URL | HTTP | Fichier de trace |
|---|---:|---|
| https://github.com/amd/xdna-driver | 200 | `evidence/urls/github.com_amd_xdna-driver.json` |

Les fetchs 1-11 ci-dessus ont **aussi** laissé leur trace JSON dans `evidence/urls/` (statut, sha256,
octets, horodatage). `check-urls` de l'oracle a par ailleurs été exécuté (voir §4).

### 1.3 Sources citées dans la littérature mais **NON vérifiées ici**

| Référence | Raison |
|---|---|
| TileFuse (Pang et al., 2026) — +121,6 % GEMM / +281 % GEMV | non retrouvée/fetchée dans cette session |
| STEEL (Jung et al., 2026) — 22,8× attention | non fetchée |
| « From Human Guidance to Autonomy » (Li et al., 2026) — 2,2× prefill / 4× decode | non fetchée |
| Docs IRON `aiex.npu.writebd` (énoncé « iteration_size biaisé de 1, iteration_stride en mots de 32 bits ») | remplacé par une **source plus forte** : le code du clone local (§2) |

> Ces trois papiers restent des **pistes** : aucune ne peut servir de preuve dans une matrice de
> verdicts tant que leur texte n'a pas été lu et rapproché d'une mesure locale.

---

## 2. Décodage BD — établi par la source, pas par une formule empirique

Source primaire **locale** (clone `E:\trixdna_test\repos_mlir_aie`), donc vérifiable et datable :

| Champ | Encodage matériel | Référence |
|---|---|---|
| `word[0]` | `buffer_length` : **unité mixte selon le chemin** — soit la longueur runtime fournie par l'appelant (`dma_task`), soit `hwS[0] × d1_size × d2_size` où `d0` est déjà converti en granules de 4 o et `d1/d2` restent des **comptes d'éléments** (`dma_memcpy_nd`). Le registre matériel, lui, compte des **mots de 32 bits** (#3033) → toute borne doit préciser son unité. | `BdLowering.cpp:197-204`, `285-287` ; #3033 |
| `word[3]` | `d0_size[29:20]` (0x3FF), `d0_stride[19:0]` (0xFFFFF) | `BdLowering.cpp:292-294` |
| `word[4]` | `burst_length[31:30]`, `d1_size[29:20]`, `d1_stride[19:0]` | `BdLowering.cpp:295-304` |
| `word[5]` | `AXCache[27:24]`, `d2_stride[19:0]` (`d2_size` implicite, porté par `buffer_length`) | `BdLowering.cpp:305-310` |
| `word[6]` | **`iteration_size[25:20]` (6 bits), `iteration_stride[19:0]`** | `BdLowering.cpp:312-322` |
| biais | `sizes[3] = inputSizes[3]-1` (« Size is stored biased by -1 ») ; `strides[i] = inStride*elemWidth/granularity - 1` | `BdLowering.h:147-149`, `180-184` |
| sémantique utilisateur | `inputWrap[3] == iteration_size + 1`, `inputStride[3] == iteration_stride / elemSizeFac + 1` | `AIEXDialect.cpp:72-73` |
| granule | `addressGranularity = 4 o` pour tout le matériel actuel | `AIEXDialect.cpp:64, 86-87` |

**Conséquence directe (RÉFUTÉ, conservé comme diagnostic)** : l'ancien modèle
`étendue = arg_plus + (payload[6] >> 16) * 0x10000 + buffer_length` de
`scripts/descriptor_bounds.py` n'est **pas** un décodage — `>>16` mélange `iteration_size` et
`iteration_stride`. Preuve par les mots : `0x0013ffff >> 16 = 0x13 = 19 = (size=1)<<4 | (stride=3)`.
Le script porte cet en-tête de réfutation et n'est plus utilisé en décision (décision →
`npu_preflight.py`).

### 2bis. Unités et association des arguments — ce qui est MESURÉ le 18/10/2026

Décodage des **64 BD patchées** de `phase5_bf16_512x8192x512_insts.bin` (`npu_preflight.bd_records`, exit 0) :

| Patch index | BD | `word[0]` | en mots de 32 bits (×4) | `d0_size`/`d1_size`/`d1_stride`/`d2_stride` | `iter_size` / `iter_stride` | somme `word[0]`×4 |
|---|---:|---:|---:|---|---|---:|
| 0 | 16 | 131 072 | **524 288 o** chacun | 64 g / 32 / 4 096 g / 64 g | 0 (1) / 0 (4 o) | **8 388 608 o** |
| 1 | 32 | 131 072 | **524 288 o** chacun | 64 g / 32 / 4 096 g / 64 g | 1 (2) / 1 048 575 (**4 194 304 o**) | **16 777 216 o** de BD, **8 388 608 o** d'étendue (8 `arg_plus` × 2 itérations) |
| 2 | 16 | 8 192 | **32 768 o** chacun | 32 g / 128 / 512 g / 256 g | 1 (2) / 65 535 (**262 144 o**) | **524 288 o** de BD, étendue décodée 795 520 o |

Faits établis :
1. **`word[0]` en mots de 32 bits** est cohérent ici : patch 0 → 16 × 524 288 = **8 388 608 o = `K·N·2`** ; patch 1 → 8 × 512 KiB × 2 itérations = **8 388 608 o**. Deux chemins indépendants retombent sur la taille logique de B (`CONFIRMÉ pour ce design`).
2. **`d1_stride` = 4 096 granules = 16 384 o = `K·2`** → deux `n` voisins sont séparés d'une ligne K entière ⇒ **K contigu** (`CONFIRMÉ`), donc stockage `(N,K)` row-major ≡ B `(K,N)` col-major.
3. **Le pas entre `arg_plus` est exactement 524 288 o** (16 patches de 0 à 7 864 320), ce qui recoupe le total ci-dessus.
4. **C est sous-estimé par la borne décodée** : 795 520 o décodés vs **1 048 576 o** mesurés (`exp_N_footprint`) — cohérent avec « la borne ignore `d0/d1/d2` », donc jamais utilisée comme majorant.

Ce qui n'est **PAS** prouvé (et ne doit pas être affirmé) :
- **L'association `bo0/bo1/bo2` ↔ A/B/C.** Elle est **déclarée par notre harnais** (`npu_gemm_ref.py:71-73` alloue `boA, boB, boC` puis `:92` `kern(3, bi, n, boA, boB, boC, 0, 0)`), pas par le design ; `kernels_main.json` ne nomme que `bo0..bo4`. A et B font **la même taille** (8 MiB) et contiennent **la même valeur** (0x3F80), donc une inversion A↔B serait **indétectable numériquement**. Conséquence : « arg1 = B » vaut **pour notre harnais**, et c'est tout ce dont le garde-fou a besoin ; la sémantique du design reste `INCONNUE` (lacune `L-X-04`).
- **Le fait que le plancher de 8 MiB soit une propriété du noyau** : `exp_P_order2` montre que la même taille sous-dimensionnée peut passer parce que la mémoire **adjacente** contenait les bonnes valeurs (A et B sont remplies de 1,0 ; `word[0]`×4 = 8 MiB). Le plancher mesuré est donc **conditionné par le voisinage d'allocation** ; seul le critère « taille ≥ taille logique » protège (`L-X-02`).

**Validation indépendante du décodage (MESURÉ, JOURNAL_PHASE_B B18-B19)** : sur
`phase5_bf16_512x8192x512_insts.bin`, `d1_stride` = 4 096 granules = 16 384 o = `K·2` →
K contigu ; recouvrement décodé = 8 `arg_plus` × 512 KiB × 2 itérations (pas 4 MiB) =
**8 388 608 o = `K·N·2`**, identique au plancher numérique mesuré. Deux chaînes indépendantes
(format ↔ mesure) donnent la même taille.

---

## 3. Matrice affirmation → preuve locale → source externe → statut

| Affirmation | Preuve locale | Réf. externe | Contradiction | Statut | Expérience discriminante manquante |
|---|---|---|---|---|---|
| `ERT_CMD_STATE_COMPLETED` ne prouve pas la justesse | exp_P : 8 372 224 o → `COMPLETED`, 512 fausses | #3653, #1645 | aucune | **CONFIRMÉ** | — (déjà tranché) |
| B sous-dimensionné ⇒ lecture hors bornes (pas écriture) | exp_N : A/B `n_changed=0`, C écrit sur `[0,1 MiB)` | Vitis (pas de témoin matériel) | aucune | **CONFIRMÉ** | localiser les octets physiques lus au-delà de B |
| `fausses = D/32` | 6 points exp_O (512 à D=16 384 o) | — | — | **CONFIRMÉ empiriquement** (dérivé §3bis) ; cause microarchitecturale **NON TESTÉE** | mesure du placement exact (`idx`) + cache/défaut de page |
| Le pas d'itération vaut 0x10000 | réfuté par décodage `word[6]` | `BdLowering.cpp:312-322` | oui | **RÉFUTÉ** (18/10/2026) | — |
| Le registre `Buffer_Length` compte des mots de 32 bits (l'attribut MLIR `len/sizes`, lui, compte des éléments) | `word[0]` = produit mixte `hwS[0]×d1×d2` (`BdLowering.cpp:197-204`) | #3033 | — | **CONFIRMÉ (source)** ; unité de `word[0]` **dépend du chemin** → à décoder, pas à supposer | confronter `word[0]` des 32 BD de B à `K·N·2/4` **et** à `K·N·2` |
| Le groupe mémoire (`group_id`) explique notre défaut B | `kern.group_id(3+i)` utilisé, `group_id=0` → crash XRT | #3653 | oui | **RÉFUTÉ (pour ce design)** | — |
| Windows/MCDM est la cause du débit GEMM | 10,8 % entre profondeur 1 et 4 | #3910 (Full-ELF ok, numérique en attente) | non tranché | **INCONCLUSIF** | trace critique complète + contrôle de l'overhead du wrapper |
| L'état persistant entre dispatches peut produire un résultat identique à une allocation correcte | exp_P order2 : même sha que la référence | #3840 | plausible | **HYPOTHÈSE** | nouveau processus + BO neufs + sentinelle + vérif de fraîcheur (GAP-2) |
| Le pré-vol est *fail-closed* quand les deux bornes sont incompatibles | **MESURÉ 18/10/2026** design 512 : `arg1` → `plancher_mesure=8 388 608`, `desaccord_descripteur=True`, et pourtant `ok=True`, `verdict=PASS`, **exit 0** | — | — | **GAP-1** : le désaccord est **signalé sans refus** (pas de `FAIL_BOUND_CONFLICT`) ; sans danger démontré ici car `max()` garantit `cible ≥ plancher mesuré` | refus explicite + test négatif ; journaliser le désaccord hors JSON aussi |
| L'oracle fournit une validation externe | il retrouve nos propres rapports (§4) | — | — | **RÉFUTÉ comme validation externe** | corpus externe indexé (issues/docs), pas nos .md |

---

## 3bis. Correction de vocabulaire (demandée par la revue) — « col-major » était ambigu

Le rapport §8bis écrivait : « B est `(N,K) = (512,8192)` col-major bf16 ». En convention
matricielle standard, `(N,K)` col-major signifie **N contigu** (512 éléments), ce qui
**contredit** K contigu (8 192) mesuré par `d1_stride` (B18). Formulation rigoureuse, sans
changer le résultat numérique :

- Le **tampon** B est un tableau `(N,K)` en **row-major** : `offset(n,k) = n·K + k` → les K
  valeurs d'un canal de sortie `n` sont **contiguës** (`b_col_maj=1`, `B_ty = ndarray[(K*N,)]`,
  `B_logical = B_np.T` — `experiment_10_phase5.py`, `EVID_D_PHASE5_GEOMETRY_2026-08-10.md`).
- Équivalemment : la matrice **logique** `(K,N)` est en **column-major** (`B_logical[k,n]` à
  l'offset `n·K + k`).
- Déficit `D` ⇒ `D/2` éléments perdus en **queue** = `(D/2)/K = D/(2K)` **canaux** ; chaque canal
  invalide les `M` sorties `C[:,n]` ⇒ `fausses = M·D/(2K) = 512·D/16384 = D/32`.
- Position : canal `n = N-1` ⇒ `idx(i) = i·N + (N-1)` (row-major C), `idx_min=511`,
  `idx_max=262 143` — exactement les indices mesurés.

Vérification arithmétique : `D = 16 384 o` ⇒ `D/2 = 8 192 = K` ⇒ 1 canal ⇒ 512 fausses (mesuré 512). ✔

Ce qui **reste non démontré** : le mécanisme physique (pourquoi les éléments manquants sont
précisément ceux du dernier canal — adresse de fin de BO vs DMA) et l'absence de tout contrôle
matériel sur XDNA2 sous Windows.

---

## 4. Oracle (skills `xdna2-evidence-oracle` / `oracle-query`) — ce qu'il fait réellement

| Commande | Résultat | Verdict |
|---|---|---|
| `oracle.py ask "<q>"` (racine par défaut) | 1 seul hit : `Desktop\xdna2-project\STRATEGIE_MCDM_BYPASS.md` (score 1) — hors sujet | **ne couvre pas ce dossier d'audit** |
| `oracle.py --root audits/xdna2-overhead-20261018 ask "<q>"` | 5 hits **de nos propres rapports** : `RAPPORT_GARDE_FOU…` (55), `JOURNAL_PHASE_B…` (25), `RAPPORT_MISSION…` (8), `AUDIT_PHASE0…` (6), `JOURNAL_EXPERIMENTAL…` (4) | **auto-cohérence**, pas validation externe |
| `oracle.py check-urls` | scanne les README d'un autre corpus (`Desktop\xdna2-project`), renvoie 200/403/NON-URL | outil d'hygiène d'URL, **pas** de contenu |

Conclusion honnête : **l'obligation « validation externe par l'oracle » n'est pas satisfaite par
l'oracle** ; elle l'est — partiellement — par les 12 lectures directes du §1.1. L'oracle reste
utile comme index de cohérence interne (retrouver quel rapport affirme quoi).

MCP/team (contexte AGENTS.md) : `flm_mcp`, `governor_mcp`, `nitro_mcp`, `rag_trixdna_mcp`,
`llamacpp_mcp` fournissent télémétrie et pont vers les runtimes ; **aucun** ne prouve une mesure
et aucun n'a été utilisé pour produire un verdict dans ce document.

---

## 5. Agents REA — les 5 rôles, mappés sur l'existant

Contrainte d'orchestration : **un seul agent peut refuser ; aucun ne peut promouvoir seul un
`COMPLETED` en `PASS_NUMERIQUE`.** Le registre commun doit contenir : sha des instructions, sha
du xclbin, versions XRT/pilote/FW/MLIR-AIE, taille de chaque BO, groupes, référence numérique,
résultat, temps médian, dispersion, statut de preuve.

| Rôle | Mission | Existant (réutilisable) | Manque (à créer) | Garde-fou actuel |
|---|---|---|---|---|
| **A1 — BD/format** | relier les mots bruts aux structures et aux champs de l'encodeur ; aucune formule empirique ne devient règle | `scripts/descriptor_bounds.py` (réfuté, conservé), `scripts/txn_dump.py`, `npu_preflight.bd_records()`/`txn_extents()` | `scripts/bd_decode.py` : décode **tous** les champs (`word[0]`, `d0/d1/d2` size+stride, burst, axcache, `iter_size/iter_stride`) selon §2, sortie JSON ; test de conformité contre un `aiecc` local | `descriptor_bounds.py` porte l'en-tête de réfutation |
| **A2 — sécurité BO** | bornes, tailles, groupes, pré-vol, refus | `scripts/npu_preflight.py`, `scripts/test_alloc_guard.py` (12/12), `scripts/audit_preflight_order.py` | **GAP-1** : refus explicite `FAIL_BOUND_CONFLICT` quand `plancher mesuré > borne décodée` — **mesuré le 18/10/2026** sur le design 512 : `arg1` porte `desaccord_descripteur=True` et le pré-vol rend quand même `PASS` / exit 0 (le `max()` protège, mais le désaccord n'est pas un refus) ; contrôle `group_id` déclaré (`kern.group_id(3+i)`) vs groupes utilisés, imprimé dans le rapport | `max(plancher, borne)` ; `PASS_SOUS_RESERVE`/`PASS_NON_CERTIFIE` jamais promus en `PASS` ; refus mesuré à 8 323 072 o (exit 3, `refused=true`) |
| **A3 — validation numérique** | comparer à une référence indépendante, conserver hashes et positions | `scripts/npu_gemm_ref.py` (262 144/262 144, exit 3 en échec), `scripts/npu_wrong_positions.py`, `scripts/npu_footprint.py` | **GAP-2** : sentinelle + vérification de fraîcheur (détecter un résultat périmé, cf. exp_P order2) ; référence CPU pour `m32k64n128` | un hash stable n'est **pas** un PASS (mesuré) |
| **A4 — performance** | mesurer le même calcul avec BO/contexte persistants ; séparer soumission, attente, transferts, exécution | `scripts/npu_gemm_loop.py` (30 soumissions, `t_soumission` vs `t_attente`), `scripts/npu_readsem.py`, `scripts/bracket_B.py` | A/B contexte persistant vs recréé (#3910) ; contrôle de l'overhead d'instrumentation (wrapper Detours, FLM #636) | ne peut pas conclure sur la correction |
| **A5 — fusion FLM** | proposer overrides/kernels fusionnés, comparer à correction numérique égale | — (aucun harnais local) | harnais A/B autour de `FLM_PLUGIN` (PR #743 : `src/plugins/iron_gemm`) : un opérateur de prefill d'abord, `decode.layer` ensuite | comparaison **uniquement** à sortie numérique égale |

Ordre de reprise recommandé (inchangé, priorisé) : **A2/GAP-1** (fail-closed, 1 test négatif) →
**A1** (`bd_decode.py`, qui débloque A2/A3) → **A3/GAP-2** (sentinelle) → **A4** (persistance) →
**A5** (plugin FLM).

---

## 6. Limites de ce document

1. 12 pages lues, 1 seule VÉRIFIÉ-HTTP ; TileFuse / STEEL / AMD-Agent **non vérifiés** (§1.3).
2. Le statut de merge de la PR #743 n'est pas affiché sur la page lue → `INCONCLUSIF`.
3. L'oracle ne constitue pas une validation externe (§4).
4. La correction de vocabulaire (§3bis) ne change **aucun** chiffre ; elle retire une ambiguïté.
5. Aucun test matériel n'a été exécuté dans cette session : les mesures citées renvoient à
   `JOURNAL_PHASE_B_2026-10-18.md` B1-B20 et à `evidence/exp_O_*`, `exp_P_*`, `exp_N_*`.

---

## 7. Reprise

```bash
cd /c/Users/videl/skills-audit-reports/audits/xdna2-overhead-20261018
I=E:/trixdna_test/repos_strixhalo_npu_setup/saved_xclbins/phase5_bf16_512x8192x512_insts.bin
python scripts/test_alloc_guard.py                                    # 12/12, exit 0
python scripts/npu_preflight.py --insts $I --sizes 16777216,8323072,16777216  # exit 3 (REFUS)
python scripts/npu_preflight.py --insts $I --sizes 16777216,8388608,16777216  # exit 0 (PASS)
python scripts/npu_wrong_positions.py --bsizes 8372224 --reps 2               # processus neuf
```

**Rejoué le 18/10/2026 dans cette session** (les 3 premières lignes) : `12/12` exit 0 ;
refus `exit 3` (`ok=false`, `refused=true`) à B = 8 323 072 o ; `PASS` `exit 0` à 8 388 608 o
(`arg1` : `plancher_mesure=8 388 608`, `cible=8 388 608`, `desaccord_descripteur=true`).
**Le chemin `--sizes` est positionnel `A,B,C`** : `--sizes 8323072` seul règle **A**, pas B —
première exécution mal interprétée puis corrigée (erreur de ma part, consignée ici).

Noms de preuve neufs à chaque campagne (`exp_Q_*`, `exp_R_*`) : ne jamais écraser `exp_O_*`/`exp_P_*`.
