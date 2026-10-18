# Garde-fou de dimensionnement, borne de C, débit boucle chaude — 18/10/2026

Audit : `xdna2-overhead-20261018`. Ce rapport ne remplace aucun rapport antérieur ;
il ajoute trois livrables et **corrige** une affirmation antérieure, avec preuve.

Matériel : XDNA2 (Strix Point), XRT 2.21.0, pyxrt, Windows. Chaque expérience est
un sous-processus distinct ; exit code réellement capturé.

---

## 1. Pré-vol de dimensionnement — désormais exécuté AVANT toute allocation

### 1.1 Règle

Dérivée des descripteurs du TXN (jamais du fait qu'un essai a réussi) :

```
étendue(arg) = arg_plus + (payload[6] >> 16) × 0x10000 + buffer_length
cible(arg)   = min(étendue(arg), plancher_mesuré(arg))      # plancher connu pour CE design
```

* `plancher_mesuré` n'est appliqué que si le **sha256 du flux d'instructions** est connu
  (`MEASURED_MIN_BY_INSTS`). Un design inconnu n'obtient aucune remise : sa cible reste
  l'étendue descripteur. Justification mesurée : le design `phase5_bf16_512x8192x512`
  adresse 7 995 392 o sur arg0, bien au-delà du plancher de 1 998 848 mesuré sur
  `m32k64n128` — appliquer le plancher en aveugle produirait un **faux PASS**.
* `npu_preflight.check()` lève `UndersizedBufferError` avant la première allocation ;
  `allow_undersized=True` est réservé aux expériences qui **testent** la borne.

### 1.2 Intégration

| Script | Appel | Mode |
|---|---|---|
| `npu_exp.py` (`map`, `sensitivity`, `patch*`) | `E.preflight(sizes, ns.insts)` | refuse (sauf `--allow-undersized`) |
| `npu_gemm_ref.py` | `E.preflight((bo,bo,bo), INSTS)` | refuse (sauf `--allow-undersized`) |
| `npu_gemm_loop.py` | `E.preflight((bo,bo,bo), INSTS)` | refuse (sauf `--allow-undersized`) |
| `bracket_B.py` (borne A/B/C) | passe `--allow-undersized` au sous-processus | teste la borne |
| `npu_run_txn.py`, `npu_patch_probe.py`, `npu_gemm_diag.py`, `npu_gemm_verify.py`, `npu_dump_c.py`, `npu_readsem.py` | `npu_preflight.check(..., allow_undersized=True)` / `E.preflight_historical(...)` | sonde fonctionnelle / tailles historiques — **affiche** le verdict, ne refuse pas |

### 1.3 Tests du garde-fou (exits réels)

| Cas | Attendu | Obtenu |
|---|---|---|
| `m32k64n128`, BO 1 998 848 / 851 968 / 544 768 | refus, exit ≠ 0 | **exit 3**, message nommant arg1 (`851 968 < 2 097 152`) et arg2 (`544 768 < 1 048 576`) |
| `npu_exp.py map` aux tailles par défaut | refus **avant** allocation | **exit 2**, `UndersizedBufferError` (aucun BO créé) |
| `m32k64n128`, C = 1 048 064 | refus (512 o manquants) | **exit 3** |
| `m32k64n128`, C = 1 048 576, A/B exacts | PASS | exit 0, `marge=+0`, mention `[plancher mesure < etendue descripteur]` |
| `phase5_bf16_512x8192x512`, 3 × 16 Mio | PASS (cible = étendue, design inconnu) | exit 0, marges +8 781 824 / +10 944 512 / +15 195 264 |
| `npu_gemm_ref.py --reps 1` | PASS numérique | `PASS_NUMERIQUE`, 262 144/262 144 valeurs = 8192.0 |

Note : le pré-vol est un **garde-fou de sûreté**, pas une preuve de justesse ; il ne dit
rien du résultat numérique (c'est le rôle de `npu_gemm_ref.py`).

---

## 2. Bornage expérimental de C — la prédiction 1 590 016 est RÉFUTÉE

Protocole : design `phase5_atb_m32k64n128` (xclbin `2139e4ad…`, insts `0a3d03e9…`),
A = 1 998 848 et B = 2 097 152 **fixes**, seule la taille de C varie ; 3 répétitions
par taille, chaque exécution en sous-processus. Critère : **nombre de mots écrits**
(pas l'égalité de hash, qui varie légitimement avec la taille allouée).

| C alloué (o) | Mio | mots écrits | octets écrits | plage | exit | état |
|---:|---:|---:|---:|---|---|---|
| 786 432 | 0,750 | 196 608 | 786 432 | [0, 196 607] | 0,0,0 | COMPLETED |
| 1 003 520 | 0,957 | 250 880 | 1 003 520 | [0, 250 879] | 0,0,0 | COMPLETED |
| 1 031 424 | 0,984 | 257 856 | 1 031 424 | [0, 257 855] | 0,0,0 | COMPLETED |
| 1 048 064 | 0,9995 | 262 016 | 1 048 064 | [0, 262 015] | 0,0,0 | COMPLETED |
| **1 048 576** | **1,000** | **262 144** | **1 048 576** | [0, 262 143] | 0,0,0 | COMPLETED |
| 1 052 672 | 1,004 | 262 144 | 1 048 576 | [0, 262 143] | 0,0,0 | COMPLETED |
| 1 572 864 | 1,500 | 262 144 | 1 048 576 | [0, 262 143] | 0,0,0 | COMPLETED |
| 1 589 760 | 1,516 | 262 144 | 1 048 576 | [0, 262 143] | 0,0,0 | COMPLETED |
| 1 590 016 | 1,516 | 262 144 | 1 048 576 | [0, 262 143] | 0,0,0 | COMPLETED |
| 1 590 528 | 1,517 | 262 144 | 1 048 576 | [0, 262 143] | 0,0,0 | COMPLETED |
| 1 638 400 | 1,562 | 262 144 | 1 048 576 | [0, 262 143] | 0,0,0 | COMPLETED |
| 2 097 152 | 2,000 | 262 144 | 1 048 576 | [0, 262 143] | 0,0,0 | COMPLETED |

36 exécutions, 36 exits 0, 36 états `ERT_CMD_STATE_COMPLETED`.

### Verdict

1. **Le pic d'écriture de C est exactement 262 144 mots = 1 048 576 o**, saturé dès
   C = 1 048 576. Premiers mots écrits identiques pour toutes les tailles (écriture
   contiguë depuis l'offset 0) ; aucune écriture au-delà de 1 MiB.
2. **C = 1 048 064 perd 128 mots (512 o)** : la frontière est nette au mot près.
3. **La prédiction issue des descripteurs (1 590 016 o) est réfutée** : elle surestime
   de **541 440 o (51,6 %)**. Cause identifiée : le pas codé en dur `0x10000` n'est pas
   le pas d'itération de l'argument 2 (les `arg_plus` des BD C avancent de `0x100`) ;
   il n'est valable que pour l'argument 1. Le modèle reste exact pour A et B.
4. **L'ancienne « borne » de C (2 Mio suffisant) ne bornait rien** : elle ne faisait que
   reproduire le succès d'un gros BO. Elle est conservée comme `ancienne_valeur` dans
   `descriptor_bounds.py` avec sa source, conformément à la règle de non-suppression.

### Conséquence pratique

C se dimensionne à `itérations × buffer_length` (16 × 64 KiB = 1 MiB) et **non** à
l'étendue des adresses. Un BO C de 1 MiB suffit ; 1,52 Mio (prédiction) gaspille
0,5 Mio par buffer dans un empilement de couches.

---

## 3. Débit en boucle chaude du GEMM phase5 validé

Protocole : `phase5_bf16_512x8192x512`, BO 16 Mio × 3, A/B remplis de BF16 1.0,
3 échauffements puis 30 soumissions chronométrées **sans synchro hôte** (données déjà
sur le device), état vérifié à chaque itération, justesse vérifiée à la fin.

| Grandeur | Valeur mesurée |
|---|---|
| état des 33 soumissions | `ERT_CMD_STATE_COMPLETED` (33/33) |
| échauffement (1er run) | 4,558 ms (froid) |
| durée totale médiane | **1,281 ms** (min 1,227 / max 1,534 / σ 0,064, n = 30) |
| dont soumission `kern()` | 0,061 ms médian (min 0,033 / max 0,240) |
| dont attente `run.wait()` | ≈ 1,22 ms |
| coût hôte H2D (3 × 16 Mio) | 0,339 ms |
| coût hôte D2H (16 Mio) | 0,315 ms |
| relecture `bo.read(16 Mio)` | **982,6 ms** (≈ 17 Mo/s) |
| justesse | 262 144/262 144 valeurs = 8192.0, 0 fausse, 0 NaN |
| sha256 de C (16 Mio) | `e43f34ad38f2044d…` |

### Comparaison au coût théorique

```
FLOP par exécution   = 2 · M · K · N = 2 · 512 · 8192 · 512 = 4,295 × 10⁹
pic revendiqué       = 58,98 TOPS  →  coût théorique 72,8 µs
mesuré               = 1 281 µs    →  écart ×17,6
débit obtenu         = 3 352,8 GFLOP/s = 3,35 TFLOP/s = 5,685 % du pic
```

**Lecture honnête.** Ce GEMM atteint 3,35 TFLOP/s, soit 5,7 % du pic BF16 annoncé ;
94,3 % du temps mesuré n'est pas du calcul idéal. Deux composantes sont déjà séparées :
la soumission (0,061 ms, 4,8 %) est faible ; le reste (≈ 1,22 ms) est le temps device
réel de ce design (8 colonnes, un seul chaînage de tuiles, sans recouvrement). Le chiffre
ne démontre donc **pas** « le NPU plafonne à 3,35 TFLOPS » : il mesure ce design-là, à
cette géométrie, sans pipelining de plusieurs soumissions.

**Piège d'outillage identifié :** relire le BO de 16 Mio prend ~1 s (17 Mo/s), soit
~780× le temps de calcul. Un banc qui relit tout le BO mesure le chemin hôte, pas le
NPU. Seuls `M·N·4 = 1 048 576 o` sont nécessaires à la vérification.

---

## 4. Fichiers produits (sha256)

| Fichier | sha256 |
|---|---|
| `scripts/npu_preflight.py` | `a72a8c0a568447c490ddf0169787b7cf0739dbb54e9d454403450cede247ffee` |
| `scripts/npu_exp.py` | `e53aa4e33606593165e6358f96eb50da41497fdf1c2a068a644cb8dc79d4ec7d` |
| `scripts/npu_gemm_ref.py` | `8cb09ce0736ec5458aa4bcb96865c43efecf63043167343ced01d11f5c1b9dc4` |
| `scripts/npu_gemm_loop.py` (nouveau, + `--depth`) | `8541355010411f75002a7d062113da68538850d9795a25ad756570487f548735` |
| `scripts/bracket_B.py` (généralisé `--vary A|B|C`) | `319d8b66bbd9d3234515534dc819fb7b0e895f60c3de250c8f81a9828c6c3da5` |
| `scripts/descriptor_bounds.py` (C corrigé, B affiné, verdicts EXACT/MAJORANT) | `5415a06d17c9ac17d5562626868c9d1fdbccabd42acd80c4209dfcab6a795178` |
| `evidence/exp_G_bracket_C.json` | `f01d23db2b260a60905d1a7720bda201f0db50ab453a28484d1c25a3649455e3` |
| `evidence/exp_G_bracket_C_small.json` | `bb79a2f79f0f8698147bdfaecb1a2b3427664fd0c8defe6d4fe7346004ce8b2f` |
| `evidence/exp_K_gemm_loop.json` | `ccf1d7d68fa8a7b2bdd4a6043a96c387818ef6510e20dab3a84cd34cb50f1e25` |
| `evidence/exp_H_gemm_ref_check.json` | `14ee5b633c958cb814559aa8c77ed318f36ac18e4bd4324d9527cb60431bdd21` |

| `evidence/exp_M_preflight_pass.json` (CLI, verdict PASS, exit 0) | `3aca31453f241b220c003392f94d278615f5178bf3161c0b386205332a943495` |
| `evidence/exp_M_preflight_refus.json` (CLI, refus, exit 3) | `b06a2f92d087db7f0a205341ac27191b20c3476108fb4509df4bd270bcda9139` |

Évidence par run : `evidence/exp_G_*_r*.json` (145 runs de borne : 109 sur B, 36 sur C),
`evidence/bracket_C.log`, et pour la boucle chaude `exp_K_gemm_loop.json` (profondeur 1),
`exp_L_gemm_depth{1,2,4}.json` (recouvrement).

**Couverture du garde-fou** : les 9 scripts qui allouent des BO (`npu_exp`, `npu_gemm_ref`,
`npu_gemm_loop`, `npu_run_txn`, `npu_patch_probe`, `npu_gemm_diag`, `npu_gemm_verify`,
`npu_dump_c`, `npu_readsem`) appellent le pré-vol avant leur première allocation ;
`bracket_B` y passe par son sous-processus `npu_exp`. Les 4 scripts restants
(`introspect_api*`, `npu_probe`, `txn_dump`) n'allouent aucun BO (vérifié par inspection :
aucun appel `pyxrt.bo(`).

---

## 4bis. Mise à jour (même journée) — B bisecté et recouvrement mesuré

### 4bis.1 Borne de B resserrée (P1)

Critère : hash de C identique sur 8 répétitions **et** exit 0 (le contenu de C est le
seul témoin sensible : le nombre de mots écrits dans C ne varie pas, cf. 4bis.2).

| B alloué (o) | Mio | répétitions | hashes distincts | verdict |
|---:|---:|---:|---:|---|
| 1 310 720 | 1,250 | 3 | 3 | échec |
| 1 769 472 | 1,687 | 3 | 3 | échec |
| 1 892 352 | 1,804 | 3 | 2 | échec |
| 1 929 216 | 1,839 | 3 | 3 | échec |
| 1 933 312 | 1,843 | 3, puis 5, puis 8 | 1 (PASS), puis 4/5, puis 8/8 | échec |
| 1 949 696 | 1,859 | 8 | 3 | échec |
| **1 966 080** | **1,875** | 8 | **1** | **PASS** |
| 1 998 848 | 1,906 | 8 | 1 | PASS |
| 2 027 520 | 1,933 | 8 | 1 | PASS |
| 2 031 616 | 1,937 | 8 | 1 | PASS |
| 2 097 152 | 2,000 | 8 | 1 | PASS |

**Verdict** : minimum reproductible de B = **1 966 080 o**, plus grand échec
1 949 696 o → borne dans un intervalle de 16 384 o (0,8 %). L'étendue descripteur
(2 097 152 o) est un **MAJORANT de 131 072 o** pour B, comme pour C.

**Enseignement de méthode** : à 3 répétitions, 1 933 312 o *passait* (1 hash unique sur 3) ;
à 5 répétitions il donne 4 hash distincts, à 8 répétitions 8 hash distincts. Les premiers
balayages à 3 répétitions **sous-estimaient donc le besoin** : la reproductibilité est un
critère statistique, 8 répétitions minimum pour une transition nette sur ce banc.

Les 145 runs de borne (109 sur B, 36 sur C) sont conservés dans `evidence/`
(`exp_G_B<taille>_r<rep>.json`, `exp_G_C<taille>_r<rep>.json`). Limite de traçabilité à
signaler : relancer un même couple taille/répétition **écrase** le fichier précédent (cas
du point 1 933 312, mesuré 3, 5 puis 8 fois) ; les résumés par lot, eux, sont tous
conservés (`exp_G_bracket_B*.json`, `exp_G_bracket_C*.json`).

### 4bis.2 Le mode d'échec n'est pas une écriture tronquée

Sur **tous** les runs B (toutes tailles confondues) : `n_changed(B) = 0` et
`n_changed(C) = 262 144` avec plage `[0, 262 143]`. Le tampon B n'est jamais écrit et
l'empreinte d'écriture de C est toujours complète. Ce qui change sous la borne, c'est le
**contenu** de C : B est lu au-delà de sa taille allouée et la valeur lue hors bornes
n'est pas reproductible. Autrement dit, sous-dimensionner B ne provoque pas une erreur
visible — il produit un résultat faux et instable. C'est exactement le mode de défaillance
qu'un garde-fou doit interdire.

### 4bis.3 Recouvrement (P2) — le design est le limiteur, pas la file

`npu_gemm_loop.py --depth N` soumet N exécutions dos à dos **avant** d'attendre :

| profondeur | durée par run (médiane) | GFLOP/s | % du pic 58,98 TOPS | hash de C |
|---:|---:|---:|---:|---|
| 1 (séquentiel) | 1,301 ms | 3 301 | 5,597 % | `e43f34ad…` |
| 2 | 1,218 ms | 3 526 | 5,979 % | `e43f34ad…` |
| 4 | **1,161 ms** | **3 699** | **6,272 %** | `e43f34ad…` |

* Gain du recouvrement : **10,8 %** (1,301 → 1,161 ms). Mettre 4 exécutions en vol ne
  divise donc pas le coût : l'écart ×17,6 au pic ne vient pas de la file de soumission.
* Le sha256 de C est **identique aux trois profondeurs** : le recouvrement ne corrompt
  pas la sortie sur ce design (aucun chevauchement d'écriture détecté).
* La dispersion chute avec la profondeur (σ 0,041 → 0,013 ms) : la file absorbe la gigue.

**Conséquence** : pour aller au-delà de ~6 % du pic il faut changer le **design**
(géométrie, colonnes, double-buffering interne), pas empiler des soumissions.

---

## 5. Ce qui est prouvé / ce qui ne l'est pas

**Prouvé**
- Un pré-vol calculé depuis les descripteurs **empêche** une allocation sous-dimensionnée
  (exit 3 avant toute allocation), pour A, B et C, sur le design étalonné.
- C exige exactement 1 048 576 o sur ce design ; 512 o de moins tronquent 128 mots.
- Le GEMM 512×8192×512 s'exécute 30 fois de suite, complète à chaque fois, résultat
  identique à la référence CPU/analytique (8192.0 partout), à 1,281 ms médian.
- Le coût hôte de relecture d'un BO de 16 Mio (≈ 1 s) domine tout le reste.
- B exige au moins 1 966 080 o sur ce design (8 répétitions/point) ; sous cette taille,
  B est lu hors bornes et C devient **faux et non reproductible** sans aucune erreur visible.
  [REQUALIFIÉ 18/10/2026, §7.3-7.5] « exige » au sens **reproductibilité** seulement : ce design
  n'a pas de référence numérique, donc 1 966 080 o n'est pas une borne de **justesse** (voir §7.3 :
  sur le design 512 qui en a une, B = 8 372 224 o donne un sha identique entre runs **avec**
  512 valeurs fausses).
- Le recouvrement de 4 exécutions ne rend que 10,8 % et ne change pas la sortie
  (sha256 de C identique) : le limiteur de débit est le design.

**Non prouvé**
- La borne de B au-delà de la résolution atteinte : minimum mesuré = 1 966 080 o,
  intervalle résiduel de 16 384 o (1 949 696 o en échec).
  [CORRIGÉ 18/10/2026, §7.4] Ce plancher est de **REPRODUCTIBILITÉ**, pas de **JUSTESSE** :
  il vient d'un test de déterminisme (`bracket_B.py`), et ce design n'a aucune référence
  numérique. Il reste une protection (il est ≥ borne décodée) mais il ne **certifie** rien —
  d'où le verdict `PASS_SOUS_RESERVE` introduit en §7.4.
- La borne de A (jamais mise en défaut ; seule l'étendue descripteur est connue).
- Le pas d'itération réel de l'argument 2 : la mesure donne la conséquence (1 MiB
  saturé), pas l'encodage du champ. Le modèle reste donc **empirique** pour C.
- La cause du plafond à ~6 % du pic : ni la file de soumission (testée à profondeur 4),
  ni la relecture hôte (hors boucle chaude). Le noyau lui-même n'a pas été instrumenté
  (pas de compteur AIE, pas de trace de cycles).
- Toute généralisation à d'autres xclbin : un seul design étalonné en détail.

---

## 6. Prochaines expériences (priorité)

1. **FAIT (P1)** — B bisecté : minimum mesuré **1 966 080 o**, plus grand échec
   1 949 696 o (8 répétitions/point, §4bis.1).
2. **FAIT (P2)** — Recouvrement mesuré aux profondeurs 1/2/4 : **+10,8 % au mieux**, sortie
   identique (§4bis.3). Le limiteur est le design, pas la file de soumission.
3. **FAIT (P1, §7.1)** — `payload[6]` **décodé** depuis les sources primaires :
   `iteration_current[31:26] | iteration_size[25:20] | iteration_stride[19:0]` (champs 6 bits
   biaisés -1, stride en granules de 4 o). L'ancien `(payload[6]>>16)*0x10000` était un
   **mélange de deux champs** — réfuté, voir §7.1.
4. **PARTIELLEMENT RÉSOLU (§7.3)** — l'écart de B n'était pas l'écart pertinent : sur **ce**
   design (m32k64n128) le plancher 1 966 080 n'était mesuré qu'au critère de **déterminisme**,
   sans référence numérique (le design n'en a pas : `npu_gemm_verify.py` y donne C ≈ 0, cos = nan).
   Sur le design 512 (qui a une référence), la borne numérique de B est
   **(8 323 072 ; 8 388 608]** o — voir §7.3.
5. **P2** — Faire varier le **design** (colonnes, tuilage, double-buffer interne) : le
   recouvrement ne rend que 10,8 %, l'essentiel du ×17,6 est dans le noyau.
6. **P2** — Réduire la relecture à `M·N·4` dans tous les bancs et re-chronométrer le
   cycle complet (calcul + vérification) au lieu du seul noyau.

---

# 7. Phase B — 18/10/2026 (session 3) : word[6] décodé, empreinte de C mesurée,
# borne B par référence numérique, défaut F-1 corrigé

Statuts utilisés : **MESURÉ** (exécuté et comparé), **DÉRIVÉ** (calculé d'une source),
**RÉFUTÉ**, **INCONCLUSIF**, **NON TESTÉ**. Aucun commit, aucun push (§7.7).

## 7.1 `payload[6]` : RÉFUTÉ comme « pas de 0x10000 », puis DÉCODÉ depuis les sources

**Réfutation (preuve par les mots, pas par l'interprétation).** Le layout réel de word[6]
pour un BD shim AIE2 (8 mots) est écrit dans la source primaire
`repos_mlir_aie/lib/Dialect/AIEX/Transforms/AIEDmaToNpu.cpp:750-760` :

```
words[6] = iteration_current[31:26] | iteration_size[25:20] | iteration_stride[19:0]
```

et l'encodeur le documente : `BdLowering.h` (« Size is stored biased by -1 »),
`AIEXDialect.cpp:66-73` (« inputWrap[3] == iteration_size + 1 », stride en granules).
L'ancienne formule `(payload[6] >> 16) * 0x10000` extrayait donc les bits 31:16, c'est-à-dire
`(iteration_size << 4) | (iteration_stride >> 16)` : un **mélange de deux champs**.
Vérification sur les mots réellement présents dans `phase5_atb_m32k64n128_insts.bin` :

| arg | word[6] réel | `>> 16` (ancienne formule) | décodage réel |
|---|---:|---:|---|
| 1 (B) | `0x0013ffff` | 19 → 19 × 0x10000 | `iter_size=1`, `iter_stride=0x3ffff` ; 19 = `(1<<4) \| 3` |
| 2 (C) | `0x0010ffff` | 16 → 16 × 0x10000 | `iter_size=1`, `iter_stride=0xffff` ; 16 = `(1<<4) \| 0` |
| 0 (A) | `0x00000000` | 0 | aucune itération |

Le « pas de 0x10000 » n'existe dans aucun champ : il tombait juste pour l'argument 1.
**Statut : RÉFUTÉ** (encodage) / **DÉCODÉ** (layout).

**Nouvelle règle du pré-vol (borne BASSE, jamais un majorant) :**

```
étendue(BD) = arg_plus + iteration_size × (iteration_stride+1) × 4 + buffer_length
```

Elle ignore le dispersement d0/d1/d2 (`d2_size` est implicite côté matériel) :
MESURÉ sur le design m32k64n128, elle vaut 1 900 544 o pour B et 803 584 o pour C — donc
**inférieure** aux besoins mesurés sur ce même design (2 097 152 et 1 048 576 o). Sur le design
512 elle vaut 7 995 392 o (A) / 7 995 392 o (B) / 795 520 o (C) : là aussi une borne basse, les
planchers mesurés restant 7 995 392 et 8 388 608 o. Elle est utilisée **en borne basse** et combinée
en `max()` avec les planchers mesurés (§7.4) ; jamais seule.

## 7.2 exp_N — empreinte RÉELLE d'écriture de C (résolution 4 octets)

`scripts/npu_footprint.py`, C alloué **4 Mio** (bien au-delà de la zone écrite), marqueur
positionnel `0xDEAD0000|i`, deux remplissages successifs (entrées = BF16 1.0, puis marqueur),
2 répétitions chacun :

```
python scripts/npu_footprint.py --sizes 1998848,2097152,4194304 \
       --json evidence/exp_N_footprint.json        # EXIT=0
```

| remplissage | BO | mots « modifiés » | plus petit offset | borne sup. écrite | plages |
|---|---|---:|---:|---:|---:|
| BF16 1.0 | A / B | (détecteur inopérant : entrées ≠ marqueur) | — | — | — |
| **marqueur** | **A** | **0** | — | **jamais écrit** | 0 |
| **marqueur** | **B** | **0** | — | **jamais écrit** | 0 |
| marqueur + 1.0 | **C** | **262 144** | **0** | **1 048 576** | **1 (contiguë)** |

* **C est écrit exactement sur `[0, 1 048 576)`**, en **une seule plage contiguë**, stable 2/2.
  La « borne 1 MiB » de §2 n'était donc pas un artefact d'allocation : c'est l'étendue exacte.
* L'empreinte est **identique** avec entrées = 1.0 et entrées = marqueur : elle ne dépend pas
  des données, seulement des descripteurs.
* A et B **ne sont jamais écrits** (`n_changed = 0`) : le NPU ne fait qu'y lire. La lecture
  hors bornes de B (§4bis.2) est donc bien une **lecture**, invisible dans une relecture du BO.
* **Statut : MESURÉ.** Preuve : `evidence/exp_N_footprint.json` + `.log` (exit 0).

## 7.3 exp_O — borne de B par RÉFÉRENCE NUMÉRIQUE (et non par reproductibilité)

Le design 512×8192×512 a une référence verrouillée : C = 262 144 × **8192.0**. Test une variable
à la fois (`--bo-map 16777216,B,16777216`), 2 répétitions par point, chaque point dans un
fichier unique :

| B alloué (o) | Mio | état ERT | valeurs correctes / 262 144 | fausses | NaN | verdict |
|---:|---:|---|---:|---:|---:|---|
| 7 995 392 | 7,625 | COMPLETED | 249 856 | 12 288 | 8 704 | FAIL (exp_M) |
| 8 126 464 | 7,750 | COMPLETED | 253 952 | 8 192 | 6 400 | **FAIL_NUMERIQUE** |
| 8 257 536 | 7,875 | COMPLETED | 258 048 | 4 096 | 3 200 | **FAIL_NUMERIQUE** |
| 8 323 072 | 7,938 | COMPLETED | 260 096 | 2 048 | 0 | **FAIL_NUMERIQUE** |
| 8 372 224 | 7,984 | COMPLETED | 261 632 | **512** | 0 | **FAIL_NUMERIQUE** |
| **8 388 608** | **8,000** | COMPLETED | **262 144** | **0** | **0** | **PASS_NUMERIQUE** (2/2) |

Deux enseignements, tous deux falsifiables et testés :

1. **Reproductible ≠ exact.** À 8 126 464 o, deux runs donnent *le même nombre* de valeurs fausses
   (8 192 + 6 400 NaN) — un critère de déterminisme conclurait « comportement stable ». À
   8 372 224 o, les deux runs ont un **sha256 identique** et pourtant **512 valeurs fausses**.
2. **DÉRIVÉ puis testé :** sur 4 points, `valeurs fausses = (8 388 608 − B) / 32`
   (16 384→512, 65 536→2 048, 131 072→4 096, 262 144→8 192). La prédiction a été **testée** à
   8 372 224 o (512 attendus) → **512 observés**. Relation validée sur 4 points, cause
   microarchitecturale **NON TESTÉE**.

→ Sur ce design la borne numérique de B est **(8 323 072 ; 8 388 608]** o, soit ≤ 8 MiB ;
le plancher conservé par le pré-vol (8 388 608) reste donc en sécurité, mais il est désormais
**NUMÉRIQUE** et non plus seulement reproductible.
Preuves : `evidence/exp_O_numeric_B_<taille>.{json,log}`, exit 3 pour les échecs (le harness
refuse un verdict PASS), exit 0 pour 8 388 608.

## 7.4 Défaut **F-1** — `min(étendue, plancher)` acceptait une taille MESURÉE fausse

**Reproduit avant correction** (`scripts/npu_preflight.py`, aucun matériel requis) :

```
python scripts/npu_preflight.py --insts <phase5_bf16_512x8192x512_insts.bin> \
       --sizes 7995392,5832704,7995392
# ancien comportement : exit 0 — arg1 cible = min(5 832 704, 8 388 608) = 5 832 704
```

Or 5 832 704 o est la taille dont l'échec numérique est mesuré (§7.3 : à 7 995 392 o, 12 288
valeurs fausses + 8 704 NaN, sha instable). Le pré-vol **acceptait donc une configuration
mesurée fausse** : borne basse décodée utilisée pour affaiblir une borne mesurée.

**Correction** : `cible = max(plancher mesuré, borne décodée)`. Une borne basse ne peut plus
réduire une borne haute mesurée. **Nature du plancher** désormais explicite :
`NUMERIQUE_ET_REPRODUCTIBLE` (design 512, §7.3) vs `REPRODUCTIBLE_SEUL` (m32k64n128, dont la
justesse n'est pas établie) → nouveau verdict **`PASS_SOUS_RESERVE`** pour le second
(`design_certifie = false`), `PASS_NON_CERTIFIE` restant pour un design sans plancher.

**Non-régression** — `scripts/test_alloc_guard.py`, **12/12**, exit 0 :

| cas | attendu | obtenu |
|---|---|---|
| T8 `--sizes 7995392,5832704,7995392` (défaut F-1) | refus | refus (cible 8 388 608) |
| T9 C = 1 048 576 / 1 048 572 | accepté / refusé | conforme (empreinte exp_N) |
| T10 insts synthétique inconnu | `PASS_NON_CERTIFIE` | conforme |
| T11 512, B = 8 388 608 | `PASS` + nature NUMÉRIQUE | conforme |
| T12 m32k64n128 | `PASS_SOUS_RESERVE`, non certifié | conforme |
| T1–T7 (contrôle d'allocation) | inchangés | 7/7 OK |

## 7.5 Croisement avec la littérature (et ce qui reste externe)

* **UG1079 (AMD), « Tiling Parameters and Buffer Descriptors »** — CONFIRME le modèle de champs :
  un BD porte des dimensions de transfert et des boucles `traversing_parameters{dimension,
  stride, wrap}` où **wrap = nombre d'éléments à parcourir** (pas une longueur). Cohérent avec
  `d0_size` = taille du transfert interne en granules et `iteration_size` = nombre de pas
  externes. Lu intégralement (`docs.amd.com`, 2026.1) — c'est la référence externe qui valide
  le sens des champs décodés en §7.1.
* **MLIR-AIE #3653** (lu sur GitHub, contenu vérifié) — classe d'échec VOISINE et **écartée comme
  cause ici** : des BO liés à `group_id = 0` au lieu des groupes déclarés par le kernel donnent
  « silently wrong results (ERT reports COMPLETED, the NPU never touches the data buffers) » et
  peuvent bloquer le NPU (Linux/Strix Halo, XRT 2.21.75). Nos harnais lient chaque BO avec
  `kern.group_id(3+i)` (log `exp_N` : `groups=[16318465, 16318464, 16318464, 16318464]` ; les
  identifiants changent à chaque enregistrement de xclbin) —
  exactement ce que l'issue recommande — et l'usage de `group_id = 0` fait planter XRT sur notre
  machine (`npu_exp.py`, commentaire du test de teardown). **Conclusion : même classe de
  défaillance (ERT COMPLETED ≠ données correctes), cause différente.**
* **MLIR-AIE #3033** (débordement de conversion de longueur DMA/BD) — **NON TESTÉ localement** :
  nous ne l'avons ni lu ni reproduit ; c'est une piste pour expliquer qu'un dimensionnement dérivé
  du descripteur soit faux (§7.1 et §4bis.2 montrent que c'est le cas), pas une preuve.
* **#3910 / #3840 / #3908 / FastFlowLM #636 & #743** — non traités dans cette session ; ils
  relèvent du chemin Full-ELF, du MemTile et du compilateur, hors du périmètre bornage/pré-vol.
* **RAG local** : `rag_bm25.search()` sur `E:\trixdna_test\rag_index.json` (686 Mo) a levé
  **`MemoryError`** sur 4 requêtes ciblées (RAM disponible 9,9 GiB / 31,3 GiB au moment du test) ;
  `E:\rag ofa\bm25_index.json` (23 Mo) se charge mais dans un format non compatible
  (`TypeError: list indices must be integers`). Substitut utilisé : recherche ciblée dans
  `E:\trixdna_test\docs\*.md` → **aucun** document local ne mentionne `iteration_stride` ni
  `word[6]`/`payload[6]` : le décodage de §7.1 est un artefact **nouveau**, sans contradiction
  locale. **RAG = BLOQUÉ (à refaire quand la mémoire sera disponible)**, non « non concluant ».

## 7.5bis CAUSE TROUVÉE et DÉMONTRÉE — pourquoi `fausses = manquant/32`, et pourquoi la même taille peut PASSER

`scripts/npu_wrong_positions.py` (nouveau) mesure la **position** des valeurs fausses, pas seulement
leur nombre. Résultat en trois points, chacun mesuré :

[CORRIGÉ 18/10/2026 — terminologie réfutée, voir §7.5ter : la formulation « B (N,K) col-major »
était FAUSSE. Le tableau physique est `(N,K)` **row-major** (K contigu), ce qui équivaut à
« B (K,N) col-major ». Le calcul ci-dessous reste valide, mais « colonnes de B » doit se lire
« **lignes du tableau stocké (N,K)** = un canal de sortie n ». Preuve : §7.5ter.]

**a) La loi n'est pas une granularité matérielle : c'est de l'arithmétique de layout.**
Le tableau physique de B est `(N, K)` = (512, 8192) de bf16 avec **K contigu** (≡ B (K,N)
col-major), donc sa taille logique est `K·N·2 = 8 388 608 o` (= 8 MiB) — exactement le plancher
mesuré. Un manque de `D` octets retire la **queue** de B, soit `D/2` éléments bf16 = `D/(2K)`
**canaux n** ; chaque canal manquant rend fausses les `M = 512` valeurs `C[:, j]` :

```
valeurs fausses = M × D/(2K) = D × M/(2K) = D/32        (M=512, K=8192)
```

Vérifié sur 6 points (7 995 392 → 24 colonnes → 12 288 ; 8 126 464 → 8 192 ; 8 257 536 → 4 096 ;
8 323 072 → 2 048 ; 8 372 224 → 512 ; 8 388 608 → 0). **La divisibilité par 32 n'a rien de
matériel : c'est `M/2K`.**

**b) La position est prédite et confirmée au mot.** À `D = 16 384` : `D/(2K) = 1` colonne manquante
→ 512 valeurs fausses, `idx_min = 511`, `idx_max = 262 143` (= dernier mot de C), soit exactement
les indices `i·N + (N−1)`, `i = 0..511` : **la dernière colonne de C**, celle qui dépend de la
dernière colonne de B. Mesure : `colonnes_touchees_si_C_rowmajor = 1` (colonne 511),
`colonnes_touchees_si_C_colmajor = 512`. Ma sous-prédiction « queue contiguë de C » est donc
**RÉFUTÉE** (C est row-major, la queue est stridée) — la forme « colonne » est la bonne.

**c) La même taille peut PASSER : la lecture hors bornes lit ce qui suit le BO.**
`evidence/exp_P_order2.json` : dans un processus qui a d'abord exécuté B = 8 388 608 o (et donc
pré-rempli de `0x3F80` la région libérée), l'exécution suivante à **B = 8 372 224 o** donne
`fausses = 0` et un **sha256 de C identique** (`399c99f6…`) à celui de l'exécution correcte à
8 MiB — un **faux PASS parfait**. Dans un processus neuf, la **même** taille donne `fausses = 512`
(`exp_P_single_8372224.json`, 2/2 répétitions, sha stable). Une seule variable change : l'état de
la mémoire **adjacente** au BO. La lecture hors bornes ne provoque donc ni faute ni erreur : elle
renvoie des octets voisins indéfinis, qui peuvent coïncider avec les bonnes données.

**Corroboration externe** : la documentation AMD (Vitis, « Debugging Memory Access Violations »,
2026.1, lue) décrit exactement cette classe — « a kernel reads or writes out of bounds of an object
or reads uninitialized memory » — et précise que la détection (`--enable-memory-check`) n'existe
que dans **l'émulateur** et dégrade les performances : **il n'y a pas de contrôle de bornes à
l'exécution sur matériel**. C'est cohérent avec nos mesures (ERT `COMPLETED`, aucune erreur) et
avec MLIR-AIE #3653 (autre cause, même classe).

**Conséquences pour le garde-fou (mesurées, appliquées)** :
1. Le seul critère sûr est **la taille** (≥ taille logique du tenseur), pas le résultat : un test
   numérique lui-même peut PASSER sur un BO sous-dimensionné (cas c).
2. La borne B correcte est `K·N·2` = 8 388 608 o — ce que le pré-vol applique déjà ; la règle
   générale qui en découle : **la cible d'un BO de données est au moins la taille logique de
   l'argument**, ce que la borne décodée ne donne pas toujours (§7.1).
3. L'écriture, elle, reste mesurable sans ambiguïté (exp_N) : C est écrit sur `[0, 1 048 576)`.

## 7.5ter Layout de B : DÉMONTRÉ par le descripteur (correction d'une erreur de vocabulaire)

Objection traitée : « en convention (N,K) column-major standard, chaque colonne contient N = 512
éléments, pas K = 8192 — donc `D/(2K)` est incohérent ». **L'objection est juste sur le
vocabulaire**, et elle est tranchée par les mots réels du flux d'instructions (pas par convention) :

B = **arg1**, 32 BD (4 charges utiles identiques × 8 `arg_plus`) décodés le 18/10/2026 dans
`phase5_bf16_512x8192x512_insts.bin` :

| champ | valeur | lecture |
|---|---|---|
| `buffer_length` | 131 072 o | 128 KiB par BD |
| `d0_size` | 64 granules = **256 o contigus**, `d0_stride` = 0 | plus petit bloc contigu |
| `d1_size` | 32 | 32 pas |
| **`d1_stride`** | 4 095+1 = 4 096 granules = **16 384 o** | **= `K·2` = 8192 × 2 o : le pas `n` vaut une ligne K entière** |
| `d2_stride` | 63+1 = 64 granules = 256 o | contigu à l'intérieur de la ligne |
| `iteration_size` (biais −1) | 1 → **2 itérations** ; `iteration_stride` = 1 048 575+1 granules = **4 194 304 o** (4 MiB) | second demi-buffer |

**Preuve 1 — contiguïté de K.** Le pas de la dimension `n` vaut **16 384 o = 8192 éléments =
`K·2`**. Si N était contigu (convention (N,K) column-major stricte, strides `[1, 512]`), deux `n`
voisins seraient à **2 o** d'écart, pas à 16 384 o. Donc : **K contigu** ⟹ le tableau physique est
`(N,K)` **row-major** (strides `[K, 1]`), autrement dit B est `(K,N)` **col-major** — c'est la
convention de `b_col_maj=1` côté IRON (
`E:\trixdna_test\repos_strixhalo_npu_setup\experiments\experiment_10_phase5.py`, qui déclare
`B_ty = np.ndarray[(K*N,)]` et `B_logical = B_np.T` ; géométrie verrouillée dans
`E:\trixdna_test\docs\EVID_D_PHASE5_GEOMETRY_2026-08-10.md` §2.1/§3).

**Preuve 2 — le décodage de `payload[6]` (sic `word[6]`) est confirmé par le recouvrement.**
8 `arg_plus` (0 → 3 670 016 o, pas 524 288 o) × 512 KiB couverts par BD = 4 MiB ; **2 itérations**
à 4 MiB de pas couvrent les **8 MiB** restants : recouvrement total = **8 388 608 o = `K·N·2`**
= la taille logique mesurée de B. Cette identité arithmétique tombe exactement avec la sémantique
décodée (« size stocké = taille − 1 », stride en granules de 4 o) — validation indépendante du
§7.1, et **non** de l'ancienne formule `(w6>>16)×0x10000`.

**Conséquence sur la cause (formulation corrigée).** Un déficit `D` retire la queue du tableau
stocké, soit `D/16 384` **lignes = `D/(2K)` canaux `n`** (un canal = un vecteur K de 16 384 o) ;
chaque canal manquant invalide `M = 512` sorties `C[i][n]` :
`fausses = M·D/(2K) = D/32` — inchangé, mais **sa raison est « lignes du stockage (N,K) row-major »,
plus « colonnes d'un tableau col-major »**. La position mesurée (dernière colonne de C row-major,
`idx = i·N + (N−1)`) est cohérente avec la disparition du **dernier `n` = 511**.

**Anomalie annexe à investiguer (NON testée)** : l'argument A sous-dimensionné (T4, A = 7 995 392 o)
a donné un PASS numérique alors que le même déficit sur B échoue. Hypothèse non vérifiée : le
tableau physique de A serait aussi `(M,K)` row-major (son `d1_stride` décodé vaut également
16 384 o = `K·2`), et la lecture hors bornes tomberait sur des octets identiques (masquage du
§7.5bis.c, les BO A et B étant tous deux remplis de `0x3F80` dans ces essais).

## 7.6 Limites de la session

* La borne numérique de B n'est affinée qu'à 64 KiB (intervalle (8 323 072 ; 8 388 608]) —
  [CORRIGÉ 18/10/2026, §7.5bis] la relation `fausses = manquant/32` **est maintenant expliquée**
  (`M/(2K)`, layout col-major de B) et sa position vérifiée au mot. Restent **non testés** :
  *quels* octets physiques la lecture hors bornes renvoie (dépendance au placement XRT), et le
  fait qu'un BO sous-dimensionné peut produire un résultat **exact en apparence** (§7.5bis.c).
* Le design m32k64n128 n'a **aucune** référence numérique : ses planchers restent de
  reproductibilité, et son empreinte C (§7.2) ne certifie que la **borne d'écriture**.
* La borne décodée (§7.1) sous-estime : elle n'inclut pas d0/d1/d2 et ne peut donc pas
  remplacer un plancher mesuré — la garantie repose toujours sur `max()`.
* 2 designs sur 37 disposent d'un plancher ; le reste tombe en `PASS_NON_CERTIFIE`.
* RAG local inaccessible (§7.5) ; sources externes lues : UG1079 et #3653 seulement.

## 7.7 État Git (vérifié, pas supposé)

* Aucun commit, aucun push effectués dans cette session ; les scripts et rapports de l'audit
  restent des fichiers de travail.
* Vérification à rejouer : `git -C /c/Users/videl/skills-audit-reports status --short` et
  `git rev-parse HEAD` (voir commande de reprise ci-dessous).

## 7.8 Commande de reprise

```bash
cd /c/Users/videl/skills-audit-reports/audits/xdna2-overhead-20261018
python scripts/test_alloc_guard.py                       # 12/12 attendus, exit 0
python scripts/npu_footprint.py --sizes 1998848,2097152,4194304 \
       --json evidence/exp_N_footprint_rerun.json        # empreinte C = 1048576
python scripts/npu_gemm_ref.py --bo-map 16777216,8388608,16777216 \
       --allow-undersized --reps 2 --json evidence/exp_O_rerun.json   # PASS_NUMERIQUE
python scripts/npu_gemm_ref.py --bo-map 16777216,8372224,16777216 \
       --allow-undersized --reps 2 --json evidence/exp_O_rerun512.json # FAIL (512 fausses)
```
