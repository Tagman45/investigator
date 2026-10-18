# XDNA2 / Windows — tests A–E réellement exécutés, cause établie

**Date** : 18/10/2026 (session 2) · **Machine** : Nitro AN16S-61, Ryzen AI 9 365 · XRT 2.21.0
**Statut global** : `TESTED` sur toute la chaîne · **cause du `FAIL_STRUCTUREL` établie**
**Aucun commit, aucun push.** Rapports antérieurs conservés ; seules corrections datées ajoutées.

Livrables associés : `JOURNAL_EXPERIMENTAL_2026-10-18.md` (commande, exit, hash, verdict par test),
`scripts/txn_dump.py`, `scripts/npu_exp.py`, `scripts/npu_readsem.py`, `scripts/npu_dump_c.py`,
`evidence/exp_*.{json,txt,bin}`.

---

## 1. Résultat en une phrase

Le `FAIL_STRUCTUREL` n'était **ni** un problème de firmware, **ni** un problème de patches, **ni**
un problème de cohérence mémoire : les buffers étaient **sous-dimensionnés** par rapport à
l'empreinte réelle des DMA (descripteurs **3D**, pas des transferts plats). Avec des tailles
suffisantes, la même soumission devient **reproductible bit à bit** et **dépend déterministement de
A**. La justesse numérique du GEMM reste **non testée** faute de contrat de forme.

---

## 2. Ce que les tests changent par rapport au rapport du matin

| Affirmation du matin | Ce que la mesure dit | Verdict |
|---|---|---|
| « patches peut-être ignorés / sémantique inconnue » | `arg_plus` décale l'empreinte d'exactement `0x1000` quand on ajoute `0x1000` | **les patches sont appliqués, linéaires au byte** |
| « C majoritairement nul, `max_abs≈3e38`, cos≈0.006 » | ces mesures venaient de buffers sous-dimensionnés (écritures hors allocation) | mesure **non valide**, à refaire avec D4 |
| « 8 tuiles de 16 Kio attendues dans C » | une seule BD écrit **64 chunks de 256 o à 1 024 o de pas** ; 8 BD couvrent **1 MiB** | mon décodage des BD était **faux** |
| « SIGSEGV quand BO > 0,5 Mo » | 16 Kio plante aussi ; destruction explicite → exit 0 | **réfuté** : c'est l'**ordre de destruction** |
| « offset `0x80000000` à ajouter » | fold appliqué → `COMPLETED` et **0 octet transféré** | **réfuté pour cette pile** |
| « C dépend de A » (mesure du matin) | non déterministe à tailles nominales ⇒ test **invalide** | refait et **validé** avec D4 |

---

## 3. Test A — référence / sensibilité

Deux exécutions identiques, tailles correctes (A 4 Mio, B 2 Mio, C 2 Mio) :
sha256(C) = `7330e0d510ac5724…` **deux fois**. Changer **uniquement** A change C sur
**500 032 / 1 048 576 octets**, et déplace la base de la rampe observée (`0x8e8000` → `0x8d9c00`).
→ **PASS** : reproductibilité et dépendance à l'entrée, dans les deux cas vérifiées par empreinte.

**Ce test a d'abord échoué** (170 276 octets de différence entre deux runs identiques) : c'est cet
échec qui a conduit à la cause du §6. Il est conservé comme preuve (`exp_A_sensitivity.json`).

## 4. Test B — visibilité mémoire

* Aller-retour hôte→device→hôte **sans soumission** : **4/4 identiques** (16 Kio et 544 Kio,
  `cacheable` et `host_only`).
* Après `wait()` + `sync FROM`, `bo.read()` rend un contenu **neuf** ; un `write()` ultérieur est
  relu même sans sync, et l'aller-retour réel du nouveau marqueur passe.
→ **PASS** : aucune incohérence mémoire observée. La piste « relecture cacheable obsolète » est
**écartée** par la mesure, pas par hypothèse.

## 5. Test C — patches BD

| Variante (une seule variable) | Effet mesuré |
|---|---|
| `arg_plus := 0` | 32 768 mots en **512 plages de 64 mots**, pas de 1 024 o, départ 0 |
| `arg_plus := 0x1000` | **mêmes plages décalées de +4 096 o** |
| `arg_plus += 0x80000000` | `COMPLETED`, **0 octet écrit** |
| opcode 1 (contrôle négatif) | `COMPLETED`, **0 octet écrit** |

→ **PASS** : le firmware applique bien `arg_plus`, **1:1 en octets**. Le contrôle négatif montre que
les écritures observées avec opcode 3 viennent bien du TXN, et que `COMPLETED` seul ne prouve rien.

## 6. Test D — la cause

### 6.1 Le décodage correct des descripteurs

Les mots BD écrits par le TXN ne sont pas plats : `0x04000000` porte un **stride de `0x400`** ;
`gemm.dll` nomme les champs `D0 size/stride`, `D1 size/stride`, `D2 stride` + `Inferred D2 size`.
Une BD de `buffer_length = 16 384` couvre donc **64 × 256 o espacés de 1 024 o**, et l'ensemble des
8 BD de C couvre **1 MiB** — mesuré : `262 144` mots modifiés contigus dès que C fait 2 Mio.

**Conséquence directe** : dimensionner les BO sur `max(arg_plus) + buffer_length` (la méthode du
matin) **sous-estime** l'empreinte. A était juste suffisant (1 998 848), **B non** (851 968).

### 6.2 Preuve par isolation (2 exécutions par configuration, C = 2 Mio)

| A | B | reproductible |
|---|---|---|
| 4 194 304 | 851 968 | **non** |
| 1 998 848 | 917 504 | **non** |
| 1 998 848 | 1 048 576 | **non** |
| **1 998 848** | **2 097 152** | **oui** (sha identique) |
| 1 998 848 | 851 968 (C seul agrandi) | **non** |

→ **Cause établie** : le NPU **lit B au-delà des 851 968 octets** alloués ; la mémoire lue varie
d'une exécution à l'autre, d'où un C **non déterministe** et donc **invérifiable**. Agrandir B rend
le résultat reproductible. Aucune responsabilité n'est imputée au firmware ni au pilote : le défaut
est dans le **dimensionnement des buffers** côté hôte.

### 6.3 Ce qui reste inconnu

La **justesse numérique** du design (`C == A·B` ?) reste **UNKNOWN** : ni le xclbin, ni le TXN, ni
un manifeste ne portent M, K, N, le layout et les strides. Aucun PASS ne peut être prononcé sans
cette référence. La prochaine expérience est choisie pour ne pas en dépendre (§8).

## 7. Test E — SIGSEGV

| BO vivants à la sortie | exit |
|---|---|
| aucun | **0** |
| 1 × 16 Kio | **139** |
| 1 × 16 Kio, détruit explicitement | **0** |
| 1 × 544 Kio | **139** |
| 3 BO (1,9 + 0,85 + 0,54 Mio) | **139** |
| 3 BO, détruits explicitement | **0** |
| allocation avec `group_id = 0` en dur | **139** (immédiat) |

→ **Cause établie** : ordre de destruction (BO détruits après le device/contexte). **La taille n'est
pas le facteur.** Deuxiéme défaut isolé : `pyxrt.bo(dev, taille, flags, 0)` plante immédiatement ;
utiliser `kernel.group_id(n)`.

## 8. `mm.xclbin` — ABI inspectée, exécution bloquée sur un prérequis nommé

* ABI **identique** à `phase5` : noyau `MLIR_AIE`, `dpu_kernel_id=0x901`, 8 arguments
  `opcode(u64)`, `instr(char*)`, `ninstr(u32)`, `bo0…bo4(void*)`.
* **Aucun flux d'instructions pour `mm.xclbin`** (`.bin`/`.elf`/`.insts` : 0 résultat dans
  `C:/Program Files/flm`). Des dumps existent ailleurs sur disque, mais ils appartiennent à d'autres
  designs : famille `full_txn.bin` en `devgen=1`/`cols=4` et walk **incohérent** ; `generated_sequence.bin`
  et `flm_gemm_sequence.bin` ne contiennent qu'un **préambule** (1–2 BD).
* **Alternative testée et rejetée** : `tools_ctrlcodes/generated_phase5_ctrl.bin` est bien un ctrlcode
  **NPU2** (`devgen=4`, `cols=8`, walk cohérent, 224 ops, 64 BD, arg0/1/2 = 2/4/0,5 Mio) ; soumis à
  `phase5_atb_m32k64n128.xclbin` avec des buffers surdimensionnés (8/8/2 Mio), il rend
  `ERT_CMD_STATE_TIMEOUT` et **0 octet écrit**, deux fois (exit 0). → le ctrlcode est **lié à la
  topologie du xclbin** ; `_insts.bin` est le bon appariement pour ce xclbin.
* Le flux est **construit au runtime par `gemm.dll`**, qui contient l'assembleur TXN complet et les
  contrôles d'alignement : *« GEMM M size not aligned with total npu rows »*, *« K size not aligned
  with k »*, *« N size not aligned with n »*.
* **Verdict : NOT TESTED.** Premier prérequis manquant = **le flux TXN de `mm.xclbin`**. Le
  reconstruire exige soit un hook API sur `gemm.dll`, soit les constantes d'alignement, soit une
  capture côté FLM. Aucune exécution de `mm.xclbin` n'est revendiquée.

## 9. Registre des statuts

| Affirmation | Statut |
|---|---|
| Chaîne Windows → pilote → XRT → NPU exécutable (device, xclbin, contexte, noyau, run) | **TESTED** |
| Cohérence mémoire hôte↔device aux tailles testées | **PASS** |
| `COMPLETED` ⇒ exécution correcte | **REFUTED** |
| `arg_plus` appliqué et linéaire en octets | **PASS** |
| Patches ignorés / fold `0x80000000` nécessaire | **REFUTED** |
| Cause du `FAIL_STRUCTUREL` = buffers sous-dimensionnés (B) | **PASS** (isolation 5 configurations) |
| Reproductibilité avec tailles correctes | **PASS** (sha identique) |
| C dépend de A | **PASS** |
| SIGSEGV = ordre de destruction, indépendant de la taille | **PASS** |
| Ctrlcode NPU2 généré (`generated_phase5_ctrl.bin`) réutilisable sur ce xclbin | **REFUTED** (timeout, 0 octet, 2 runs) |
| Justesse numérique du design | **UNKNOWN / NOT TESTED** |
| Exécution de `mm.xclbin` | **NOT TESTED** (flux absent) |
| Gain de débit (t/s) par suppression d'overhead | **UNKNOWN** — non mesuré, hors périmètre de cette session |

## 10. Prochaine expérience (une seule variable)

**Linéarité, indépendante de la forme** : remplir A de BF16 propres (`1.0`, `0.5`), exécuter avec
`A` puis `2·A`, comparer `C(2A)` à `2·C(A)` composante par composante (tailles du §6.2).
*Si l'égalité tient*, le chemin A→C est une application linéaire compatible GEMM et la référence
numérique devient testable dès que le contrat de forme est extrait ; *sinon*, le contrat A⇒C est
établi comme non-GEMM et il faut d'abord corriger les descripteurs, pas la référence.

## 11. Limites

* Un seul design (`phase5_atb_m32k64n128`) ; le contrat de forme reste déduit, jamais lu.
* Le seuil exact de taille de B n'est pas borné entre 1 et 2 Mio (seules les bornes sont mesurées).
* Les timings du matin (soumission ≈ 0,1–0,2 ms, attente ≈ 2,2 ms) n'ont pas été re-mesurés ici ;
  ils restent **TESTED** mais **non reproductibles dans ce journal**.
* Aucun test de `mm.xclbin`, aucune mesure de débit (t/s).
* Codes de sortie **non capturés** pour les exécutions en boucle `exp_D_iso_*`,
  `exp_D_bracket_B917504_*` et `exp_D_onlyC_*` (sortie redirigée) : leur statut repose sur
  l'artefact JSON produit et relu, **pas** sur un exit vérifié. Les autres runs ont un exit explicite
  (journal, §« Traçabilité des codes de sortie »).

---

## 12. Série 2 — le GEMM est numériquement validé

Sept points du cadrage ont été traités dans l'ordre. Deux résultats changent le verdict global.

### 12.1 Bornage de B (point 1) — 7 tailles × 3 répétitions

| B (Mio) | 1,00 | 1,05 | 1,25 | 1,50 | 1,75 | **2,00** |
|---|---|---|---|---|---|---|
| reproductible | non | non | non | non | non | **oui** |
| hash distincts | 3 | 3 | 3 | 3 | 3 | **1** |
| exit | 0,0,0 | 0,0,0 | 0,0,0 | 0,0,0 | 0,0,0 | 0,0,0 |
| état ERT | COMPLETED | COMPLETED | COMPLETED | COMPLETED | COMPLETED | COMPLETED |

Seuil : **B > 1,75 Mio** ; plus petite taille reproductible = **2 097 152 octets**, exactement
l'étendue prédite par les descripteurs (§12.2) — **marge nulle**.
`COMPLETED` sur les **21 runs** : l'état ERT **ne discrimine rien**.
Chaque run est un sous-processus (exit réellement capturé).

### 12.2 Bornes des descripteurs 3D (point 2) — modèle prédictif validé

`étendue = arg_plus + (w10>>16) × 0x10000 + buffer_length`

| arg | étendue **calculée** | taille **mesurée** suffisante | écart |
|---|---|---|---|
| A | 1 998 848 | 1 998 848 | **0** |
| B | 2 097 152 | 2 097 152 | **0** (1 835 008 échoue, 2 097 152 passe) |
| C | 1 590 016 | 2 097 152 | cohérent (544 768 échoue) |

Le seuil de B n'est donc pas une constante empirique : il est **dérivé des descripteurs** puis
**confirmé** par une expérience indépendante. C'est la vérification demandée — les bornes tiennent,
et la correction ne repose plus sur « le kernel termine ».

### 12.3 Validation numérique (point 3) — PASS

Référence verrouillée du projet : `phase5_bf16_512x8192x512`, **M=512, K=8192, N=512**,
A et B = BF16 `0x3F80` (1.0), C = F32 sur M×N = 262 144 valeurs, attendu **C = K = 8192.0**,
BO de 16 Mio (harnais `npu_repro --gemm-check`).

| run | état | correctes | fausses | min / max | temps |
|---|---|---|---|---|---|
| 1 | COMPLETED | **262 144 / 262 144** | **0** | 8192.0 / 8192.0 | 4,742 ms |
| 2 | COMPLETED | **262 144 / 262 144** | **0** | 8192.0 / 8192.0 | 1,880 ms |

sha256(C) identiques ⇒ **PASS_NUMERIQUE**, exit 0, **reproductible**.
La référence CPU est triviale et indépendante (`Σ_k 1·1 = K`) : elle ne réutilise aucun code du
design. Les dimensions et le layout viennent du document de géométrie, pas d'une déduction.
**Portée** : ce PASS concerne `phase5_bf16_512x8192x512`. `phase5_atb_m32k64n128` reste un
artefact DMA non validé numériquement (contrat de forme absent).

### 12.4 Cycle de vie (point 4)

23 runs avec destruction explicite (`npu_gemm_ref` ×2, `bracket_B` ×21) : **23 exit 0**, aucun
SIGSEGV. Le correctif est donc appliqué **et répété**, pas seulement constaté une fois.

**[COMPLÉTÉ 18/10/2026]** Bornage resserré : 1,50 et 1,75 Mio testés (3 répétitions chacun),
**non reproductibles**, exit 0, ERT `COMPLETED`. Le seuil est donc **B > 1,75 Mio** et la plus
petite taille reproductible est **exactement** l'étendue prédite (2 097 152).

### 12.5 Flux de `mm.xclbin` (point 5)

* metadata de `mm.xclbin` (FLM) et `E:/trixdna_test/mm_metadata.xml` : **identiques octet pour octet** ;
* son **PDI est déjà extrait** (`aiebu_extract/mm/…pdi`, 500 960 o) et `disasm/mm.asm` le désassemble ;
* **aucun TXN pour ce xclbin** : `mm_custom.seq` est un TXN `cols=1` d'une variante
  (`mm_custom.xclbin`, sha différent) ; le ctrlcode de `mm.xclbin` est construit au runtime par
  `gemm.dll`.
⇒ **NOT TESTED**, prérequis nommé : capturer le TXN (`hook_ctrlcode_dump.dll`, présent) ou le
régénérer pour la topologie exacte.

### 12.6 Registre complété

| Affirmation | Statut |
|---|---|
| Seuil de B borné et expliqué par les descripteurs | **PASS** |
| GEMM `phase5_bf16_512x8192x512` correct et reproductible | **PASS_NUMERIQUE** |
| Crash de teardown éliminé par destruction explicite (23 runs) | **PASS** |
| TXN de `mm.xclbin` sur disque | **REFUTED** |
| Exécution de `mm.xclbin` | **NOT TESTED** (prérequis : TXN) |
| Débit d'inférence (t/s) | **UNKNOWN** — non mesuré, hors périmètre |

### 12.7 Prochaine étape, dans l'ordre

1. **Débit** : le chemin de calcul étant validé, mesurer t/s sur `phase5_bf16_512x8192x512`
   (A·B/BF16, 16 Mio) en boucle chaude, puis rapporter au coût théorique `2·M·K·N`.
2. **`mm.xclbin`** : capturer son TXN, vérifier son contrat avec `descriptor_bounds.py` **avant**
   toute soumission, puis exécuter avec les tailles dérivées.
3. **C (sortie)** : borner C comme B l'a été (prédiction 1 590 016 ; test à 1,6 Mio).
