# Journal de progression — Phase B (session 3) — 18/10/2026

Audit : `audits/xdna2-overhead-20261018` (mission : identifier et éliminer les surcoûts et
défauts du runtime NPU XDNA2 sous Windows).
**Aucun commit, aucun push.** Aucun fichier de preuve antérieur supprimé ou écrasé : les
nouveaux résultats utilisent des noms uniques (`exp_N_*`, `exp_O_*`).

Statuts : MESURÉ / DÉRIVÉ / RÉFUTÉ / INCONCLUSIF / NON TESTÉ.

---

## 1. Reprise : ce que la session précédente laissait ouvert

| Piste laissée ouverte | Traitement Phase B | Statut |
|---|---|---|
| Décoder `payload[6]` (P1) | §3 : layout décodé depuis les sources, ancienne formule réfutée | **FAIT** |
| Étendue exacte de C | §4 : empreinte mesurée au mot | **FAIT** |
| Borne de B « mesurée » à 1 966 080 o | §5 : re-mesurée **au critère numérique** sur le design 512 | **REQUALIFIÉ** |
| Garde-fou `min(étendue, plancher)` | §6 : trou F-1 reproduit puis corrigé en `max()` | **CORRIGÉ** |

## 2. Tâches et commandes (horodaté, avec code de sortie)

| # | Commande | Résultat | Exit |
|---|---|---|---|
| B1 | `python scripts/descriptor_bounds.py --json evidence/_tmp_db.json` | 40 BD, 3 arguments, anciennes étendues (0x1e8000 / 0x200000 / 0x184300) | 0 |
| B2 | dump des mots de BD (analysis, pas de script créé) | `w6` réels : arg0 `0x00000000`, arg1 `0x0013ffff`, arg2 `0x0010ffff` | 0 |
| B3 | `python scripts/npu_footprint.py --sizes 1998848,2097152,4194304 --json evidence/exp_N_footprint.json` | C écrit sur `[0, 1 048 576)`, 1 plage, stable 2/2 ; A/B jamais écrits | 0 |
| B4 | `python scripts/npu_gemm_ref.py --bo-map 16777216,8388608,16777216 --allow-undersized --reps 2` | 262 144/262 144 correctes, 0 NaN, sha stable → **PASS_NUMERIQUE** | 0 |
| B5 | idem `B = 8 126 464` | 253 952 correctes, 8 192 fausses, 6 400 NaN → FAIL_NUMERIQUE | 3 |
| B6 | idem `B = 8 323 072` | 260 096 correctes, 2 048 fausses → FAIL_NUMERIQUE | 3 |
| B7 | idem `B = 8 257 536` | 258 048 correctes, 4 096 fausses → FAIL_NUMERIQUE | 3 |
| B8 | idem `B = 8 372 224` (**test de prédiction**) | 512 fausses (prédit 512) → FAIL_NUMERIQUE, sha **stable** | 3 |
| B9 | `python scripts/npu_preflight.py --insts <512_insts> --sizes 7995392,5832704,7995392` (avant correction) | accepté → **défaut F-1** | **0** |
| B10 | `python scripts/test_alloc_guard.py` (après correction) | **12/12 cas OK** | 0 |
| B11 | RAG : `rag_bm25.search(E:\trixdna_test\rag_index.json, ...)` ×4 requêtes | `MemoryError` (686 Mo d'index ; 9,9 GiB libres) | 0 |
| B12 | RAG OFA : `BM25.load(E:\rag ofa\bm25_index.json)` | chargé mais format incompatible (`TypeError`) | 0 |
| B13 | `grep -rln "iteration_stride" E:\trixdna_test\docs\*.md` | 0 fichier ; idem `word[6]`/`payload[6]` → décodage **nouveau** | 1 |
| B14 | `python -u scripts/npu_wrong_positions.py --bsizes 8372224 --reps 2` (processus neuf) | `fausses=512` (= prédit), `idx_min=511`, `idx_max=262143`, colonne 511 seule, sha stable | 0 |
| B15 | idem `--bsizes 8388608,8372224` (même taille en SECOND) | **`fausses=0`** et sha **identique** à la taille correcte (`399c99f6`) → **faux PASS** | 3 |
| B16 | `python -u scripts/npu_wrong_positions.py --bsizes 8388608,8372224,8323072` | les 3 tailles → `fausses=0` (mémoire adjacente pré-remplie) | 3 |
| B17 | docs AMD « Debugging Memory Access Violations » (2026.1) | la détection hors-bornes n'existe **que** dans l'émulateur, pas à l'exécution matérielle | 0 |
| B18 | décodage des 32 BD d'arg1 (B) dans `phase5_bf16_512x8192x512_insts.bin` (`npu_preflight.bd_records`) | **`d1_stride` = 4 096 granules = 16 384 o = `K·2`** → K contigu ; `d0_size`=64 g (256 o), `d2_stride`=256 o, `iter`=2×4 MiB | 0 |
| B19 | confrontation du recouvrement décodé à la taille mesurée de B | 8 `arg_plus` × 512 KiB = 4 MiB, × 2 itérations (pas 4 MiB) = **8 388 608 o = `K·N·2`** → décodage de word[6] validé par identité indépendante | 0 |
| B20 | `experiment_10_phase5.py` + `EVID_D_PHASE5_GEOMETRY_2026-08-10.md` | `b_col_maj=1` → `B_ty = np.ndarray[(K*N,)]`, `B_logical = B_np.T` : confirme « K contigu » | 0 |

## 3. Décodage de `payload[6]` (MESURÉ + source primaire)

* Source : `AIEDmaToNpu.cpp:750-760` (`words[6] = iter_current[31:26] | iter_size[25:20] |
  iter_stride[19:0]`), `BdLowering.h` (« Size is stored biased by -1 »),
  `AIEXDialect.cpp:66-73` (`inputWrap[3] == iteration_size + 1`, stride en granules de 4 o).
* Preuve par les mots : `0x0013ffff >> 16 = 0x13 = 19 = (iter_size=1 << 4) | 3` → l'ancienne
  formule mélangeait deux champs. **RÉFUTÉ** comme pas d'itération.
* Nouvelle borne basse : `arg_plus + iter_size × (iter_stride+1) × 4 + buffer_length`
  → 1 900 544 o (B) et 803 584 o (C) sur m32k64n128 : **inférieure** aux besoins mesurés,
  donc utilisée uniquement en `max()` avec les planchers mesurés.

## 4. exp_N — empreinte exacte de C (MESURÉ)

* Avec entrées = BF16 1.0 **et** avec entrées = marqueur : C est écrit **exactement** sur
  `[0, 1 048 576)` (262 144 mots), **une seule plage contiguë**, stable 2/2.
* A et B : `n_changed = 0` → **jamais écrits** ; l'échec de B sous-dimensionné est donc bien
  une **lecture** hors bornes (invisible dans une relecture de B).
* Conséquence : la « borne 1 MiB » devient une **étendue mesurée exacte** (T9 la teste à ±4 o).

## 5. exp_O — borne de B au critère NUMÉRIQUE (MESURÉ)

| B (o) | correctes / 262 144 | fausses | NaN | verdict |
|---:|---:|---:|---:|---|
| 7 995 392 | 249 856 | 12 288 | 8 704 | FAIL |
| 8 126 464 | 253 952 | 8 192 | 6 400 | FAIL |
| 8 257 536 | 258 048 | 4 096 | 3 200 | FAIL |
| 8 323 072 | 260 096 | 2 048 | 0 | FAIL |
| 8 372 224 | 261 632 | **512** (prédit 512) | 0 | FAIL |
| 8 388 608 | **262 144** | **0** | **0** | **PASS** (2/2) |

* **Reproductible ≠ exact** : à 8 372 224 o les deux runs ont un **sha identique** et pourtant
  512 valeurs fausses ; à 8 126 464 o le *nombre* de valeurs fausses est identique entre runs.
* **DÉRIVÉ + testé** : `fausses = (8 388 608 − B)/32` sur 4 points, prédiction vérifiée au 5e.
* Cause microarchitecturale de cette relation : **NON TESTÉE**.

## 6. Défaut F-1 et correction (MESURÉ)

* Avant : `cible = min(étendue, plancher)` → `--sizes 7995392,5832704,7995392` **exit 0** alors
  que 5 832 704 o est mesuré faux : la borne basse affaiblissait une borne haute mesurée.
* Après : `cible = max(plancher mesuré, borne décodée)`.
* **Nature du plancher** : `NUMERIQUE_ET_REPRODUCTIBLE` (design 512) vs `REPRODUCTIBLE_SEUL`
  (m32k64n128, aucune référence numérique) → verdict `PASS_SOUS_RESERVE`, `design_certifie=false`.
* Tests négatifs : **12/12** (T8 = non-régression F-1, T9 = empreinte C ±4 o, T10 = design
  inconnu, T11 = plancher numérique ⇒ `PASS`, T12 = plancher de reproductibilité ⇒
  `PASS_SOUS_RESERVE`).

## 7. Croisement littérature / sources externes

* **UG1079 (AMD)** « Tiling Parameters and Buffer Descriptors » (lu, 2026.1) : `traversing_parameters`
  = `{dimension, stride, wrap}` avec **wrap = nombre d'éléments à parcourir** → confirme le sens
  des champs décodés (§3) ; connexe.
* **MLIR-AIE #3653** (lue, contenu vérifié) : BO liés à `group_id = 0` → « silently wrong results
  (ERT reports COMPLETED…) » sur Linux/Strix Halo. **Cause écartée ici** : nos harnais passent
  `kern.group_id(3+i)` (log `exp_N` : `groups=[16318465, 16318464, 16318464, 16318464]` ; les
  identifiants changent à chaque enregistrement de xclbin), et
  `group_id = 0` provoque un crash XRT sur notre machine.
* **MLIR-AIE #3033** (longueur DMA) : **NON TESTÉ** localement — piste, pas preuve.
* **#3910 / #3840 / #3908 / FLM #636 & #743** : hors périmètre session (NON TESTÉ).
  **[COMPLÉTÉ 18/10/2026]** ces 5 pages sont désormais **lues** (passages cités) → voir
  `SOURCES_URLS_ET_AGENTS_2026-10-18.md` §1.1 ; elles restent **NON TESTÉES localement** :
  #3910 fournit une séquence Full-ELF répétable sous Windows mais « numerical correctness still
  pending » ; #3840 documente un état persistant (MemTile col-0) qui reste une **hypothèse** pour
  notre faux PASS ; #3908 ne concerne que le temps de compilation ; FLM #743 donne un mécanisme
  d'override d'opérateurs (statut de merge **non affiché** sur la page lue).
* **Décodage BD ancré dans le code local** (nouveau, vérifié 18/10/2026) : `word[6]` =
  `iteration_size[25:20] | iteration_stride[19:0]` (`BdLowering.cpp:312-322`), `word[3]/[4]/[5]` =
  `d0/d1/d2` size+stride (`:292-310`), biais `-1` (`BdLowering.h:147-149`, `180-184`),
  `inputWrap[3] == iteration_size + 1` (`AIEXDialect.cpp:72-73`). `word[0]` (`buffer_length`) a une
  **unité mixte** selon le chemin (`BdLowering.cpp:197-204`) : à décoder, pas à supposer. Ces
  références remplacent l'énoncé de doc IRON non vérifié.
* **RAG local** : BLOQUÉ (`MemoryError`), canal de substitution = grep ciblé de
  `E:\trixdna_test\docs\*.md` → aucun doc local ne traite `iteration_stride`/`word[6]`.

## 8. Limites assumées

1. Borne numérique de B affinée à 64 KiB seulement : (8 323 072 ; 8 388 608].
2. La relation `fausses = manquant/32` est DÉRIVÉE et validée empiriquement, **pas expliquée**.
3. m32k64n128 n'a **aucune** référence numérique ; ses planchers ne certifient rien.
4. La borne décodée ignore d0/d1/d2 : elle ne peut jamais servir de majorant.
5. 2 designs sur 37 ont un plancher ; RAG local inaccessible ; sources externes limitées à 2 lues.

## 8bis. CAUSE TROUVÉE (exp_P, MESURÉ) — pourquoi `fausses = manquant/32`

1. **Layout, pas granularité matérielle.** B est `(N, K) = (512, 8192)` col-major bf16 → taille
   logique `K·N·2` = **8 388 608 o** = le plancher mesuré. Un manque de `D` octets coupe la queue
   de B = `D/2` éléments = `D/(2K)` **colonnes** ; chaque colonne manquante invalide `M = 512`
   sorties → `fausses = M·D/(2K) = D/32` (`M/2K = 512/16384`). Vérifié sur 6 points.
2. **Position confirmée au mot.** `D = 16 384` → 1 colonne → `fausses = 512`, indices
   `i·N + (N−1)` : `idx_min = 511`, `idx_max = 262 143` = dernier mot de C. Ma sous-prédiction
   « queue contiguë de C » est **RÉFUTÉE** (C row-major) ; la forme « dernière colonne » est la bonne.
3. **La même taille peut PASSER.** Même processus : B = 8 388 608 o déroulé d'abord, puis
   B = 8 372 224 o → `fausses = 0` et **sha de C identique** à la sortie correcte (`399c99f6`) =
   **faux PASS**. Processus neuf, même taille → `fausses = 512`. Une seule variable : la mémoire
   **adjacente** au BO. La lecture hors bornes ne faute pas, elle lit des octets voisins indéfinis.
4. **Corroboration externe** : doc AMD Vitis/Debugging Memory Access Violations — détection
   hors-bornes = émulateur seulement, **pas de contrôle à l'exécution matérielle**.
5. **Conséquence** : seul le critère **taille** est sûr (≥ taille logique du tenseur) ; un test
   numérique peut lui-même passer sur un BO sous-dimensionné (point 3).

## 8ter. CORRECTION de vocabulaire (18/10/2026) — le layout de B est DÉMONTRÉ

La formulation du §8bis (« B (N,K) col-major ») était **fausse en vocabulaire** (en col-major
standard, (N,K) impliquerait N contigu, soit 512 éléments par colonne). Objection traitée par le
décodage des 32 BD de B :

* `d1_stride = 4 095+1 granules × 4 = 16 384 o = K·2` → deux `n` voisins sont séparés d'une **ligne
  K entière** ; en col-major strict ils seraient à 2 o. Donc **K est contigu** : le stockage est
  `(N,K)` **row-major** (strides `[K,1]`), ce qui équivaut à « B (K,N) col-major » (b_col_maj=1).
* `d0_size` = 64 granules = 256 o contigus, `d2_stride` = 256 o (contiguïté intra-ligne),
  `iteration_size` = 1 → 2 itérations de pas 4 MiB.
* **Validation indépendante du §3** : 8 `arg_plus` (0 → 3 670 016, pas 524 288 = 32 × 16 384) ×
  512 KiB = 4 MiB, × 2 itérations = **8 MiB = `K·N·2`** = taille logique mesurée de B.
* Conséquence : `fausses = M·D/(2K) = D/32` reste vrai, mais la raison est « **`D/16 384` lignes du
  stockage (N,K) = autant de canaux `n`** », pas « colonnes d'un col-major ». La position mesurée
  (`C[i][N−1]`) = disparition du **dernier canal n = 511**.
* Anomalie NON testée : A sous-dimensionné passe le test numérique (T4) alors que B échoue au même
  déficit ; son `d1_stride` vaut aussi 16 384 o = `K·2`. Hypothèse (masquage par des octets
  identiques, §8bis.3) **non vérifiée**.

## 9. Prochaine action (choisie automatiquement)

**P1** — établir une référence numérique pour le design m32k64n128 (`npu_gemm_verify.py` y donne
`cos = nan` et `C ≈ 0`) : sans référence, ses planchers restent de reproductibilité et tout
verdict y est `PASS_SOUS_RESERVE`. Le test minimal est de confronter la sortie C à une référence
CPU calculée pour des entrées connues **et** à l'invariant d'écriture mesuré en §4.
